import asyncio
from typing import Any

from common.database.postgres_database import AsyncSessionLocal
from common.database.repository import refresh_job_leases
from common.services.queue_services.base import QueueService
from common.settings import get_settings, get_structured_logger
from common.types import TaskType, WorkerMessage
from worker.healthcheck import HEARTBEAT_DIR, ensure_heartbeat_dir
from worker.signal_handler import SignalHandler
from worker.workflows.edit_minute_version import edit_minute_version
from worker.workflows.generate_minute_version import generate_minute_version

slogger = get_structured_logger()


class Consumer:
    """Single-queue asyncio consumer: one in-flight asyncio task per received message,
    bounded by the sum of the per-phase semaphores. The per-job heartbeat keeps the
    message invisible (SQS visibility extension) AND renews the database lease
    (claimed_at), so a legitimately long job is never redelivered and its claim can
    never be stolen by a duplicate message while its worker is alive. When the worker
    dies, both signals stop: the message redelivers within one visibility window and
    the claim becomes stealable after the staleness window."""

    def __init__(self, queue_service: QueueService, signal_handler: SignalHandler) -> None:
        settings = get_settings()
        self.queue = queue_service
        self.signal_handler = signal_handler
        self.transcription_slot = asyncio.Semaphore(settings.MAX_CONCURRENT_TRANSCRIPTIONS)
        self.llm_slot = asyncio.Semaphore(settings.MAX_CONCURRENT_LLM)
        self.capacity = asyncio.Semaphore(settings.MAX_CONCURRENT_TRANSCRIPTIONS + settings.MAX_CONCURRENT_LLM)
        self.visibility_seconds = settings.JOB_VISIBILITY_TIMEOUT_SECS
        self.heartbeat_interval = settings.JOB_HEARTBEAT_INTERVAL_SECS
        self.stale_seconds = settings.JOB_STALE_SECONDS
        self.tasks: set[asyncio.Task] = set()
        self.heartbeat_path = HEARTBEAT_DIR / "worker_consumer.heartbeat"

    def _touch(self) -> None:
        """Liveness signal for the ECS healthcheck; must never break job processing."""
        try:
            ensure_heartbeat_dir()
            self.heartbeat_path.touch()
        except OSError:
            slogger.exception("Could not write liveness heartbeat")

    async def run(self) -> None:
        ensure_heartbeat_dir()
        self.heartbeat_path.touch()
        settings = get_settings()
        slogger.info(
            "Consumer started: queue={queue} max_transcriptions={max_transcriptions} max_llm={max_llm} "
            "visibility={visibility} heartbeat={heartbeat} stale={stale}",
            queue=getattr(self.queue, "name", "?"),
            max_transcriptions=settings.MAX_CONCURRENT_TRANSCRIPTIONS,
            max_llm=settings.MAX_CONCURRENT_LLM,
            visibility=self.visibility_seconds,
            heartbeat=self.heartbeat_interval,
            stale=self.stale_seconds,
        )
        while not self.signal_handler.signal_received:
            await self.capacity.acquire()
            try:
                messages = await asyncio.to_thread(self.queue.receive_message, 1)
            except Exception:
                self.capacity.release()
                slogger.exception("Receiving messages failed")
                self._touch()
                await asyncio.sleep(1)
                continue
            if not messages:
                self.capacity.release()
                self._touch()
                continue
            message, receipt = messages[0]
            task = asyncio.create_task(self._process(message, receipt))
            self.tasks.add(task)
            task.add_done_callback(self._task_done)
        await self._drain()
        slogger.info("Worker stopped")

    async def _drain(self) -> None:
        slogger.info("Shutdown signal received, waiting for {count} in-flight jobs", count=len(self.tasks))
        while self.tasks:
            await asyncio.wait(self.tasks, timeout=1)

    def _task_done(self, task: asyncio.Task) -> None:
        self.tasks.discard(task)
        self.capacity.release()
        self._touch()
        if not task.cancelled() and task.exception():
            slogger.error("Job task ended unexpectedly: {error}", error=str(task.exception()))

    async def _heartbeat(self, receipt_handle: Any, minute_version_id: Any) -> None:
        """Keep the job alive on both liveness signals while it runs:
        - SQS visibility extension: the message is never redelivered mid-run;
        - claimed_at renewal: the claim can never be stolen by a duplicate message.
        A tick failing on one signal (or both) degrades to redelivery after the
        visibility window, which the claim CAS makes safe. Created inside the job's
        task, so these warnings carry the context bound so far (minute_version_id;
        the workflow binds the remaining entity ids later)."""
        try:
            while True:
                await asyncio.sleep(self.heartbeat_interval)
                try:
                    await asyncio.to_thread(self.queue.extend_message, receipt_handle, self.visibility_seconds)
                except Exception:  # noqa: BLE001 - one failed tick must not kill the heartbeat
                    slogger.warning("SQS visibility extension failed")
                try:
                    async with AsyncSessionLocal() as session:
                        await refresh_job_leases(session, minute_version_id)
                        await session.commit()
                except Exception:  # noqa: BLE001 - one failed tick must not kill the heartbeat
                    slogger.warning("Lease renewal failed")
        except asyncio.CancelledError:
            raise

    async def _process(self, message: WorkerMessage, receipt_handle: Any) -> None:
        # Task-local log context (structlog.contextvars): every log line emitted for
        # this job, including from workflows/actions and the heartbeat task, carries
        # these fields without cross-talk between concurrent jobs.
        slogger.refresh_context()
        slogger.set_context_field("minute_version_id", str(message.id))
        slogger.info("Received {task_type} job", task_type=getattr(message.type, "name", str(message.type)))
        heartbeat = asyncio.create_task(self._heartbeat(receipt_handle, message.id))
        try:
            match message.type:
                case TaskType.MINUTE:
                    outcome = await generate_minute_version(
                        message.id, self.transcription_slot, self.llm_slot, self.stale_seconds
                    )
                case TaskType.EDIT:
                    if message.data is None:
                        slogger.warning("EDIT message missing source data")
                        await asyncio.to_thread(self.queue.deadletter_message, message, receipt_handle)
                        return
                    outcome = await edit_minute_version(
                        message.id, message.data.source_id, self.llm_slot, self.stale_seconds
                    )
                case _:
                    slogger.warning("Unknown task type: {task_type}", task_type=str(message.type))
                    await asyncio.to_thread(self.queue.deadletter_message, message, receipt_handle)
                    return
        except Exception:
            # Nothing was recorded in the database for this failure (the workflows record
            # and re-raise their own handled failures). Hide the message and let it
            # redeliver; the DLQ redrive catches true poison after repeated attempts.
            slogger.exception("Job processing crashed")
            await asyncio.to_thread(self.queue.extend_message, receipt_handle, self.visibility_seconds)
            return
        finally:
            heartbeat.cancel()
            self._touch()

        if outcome == "delete":
            await asyncio.to_thread(self.queue.complete_message, receipt_handle)
            slogger.info("Job handled: message deleted")
        else:
            # Another consumer owns this job; hide our copy until it finishes.
            await asyncio.to_thread(self.queue.extend_message, receipt_handle, self.visibility_seconds)
            slogger.info("Job owned by another worker: message rehidden")

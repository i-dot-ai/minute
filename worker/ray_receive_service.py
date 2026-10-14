import asyncio
import logging
from typing import Any

import ray

from common.sentry import init_sentry
from common.services.exceptions import TranscriptionFailedError
from common.services.minute_handler_service import MinuteDelivery, MinuteGenerationFailedError, MinuteHandlerService
from common.services.queue_services.base import QueueService
from common.services.transcription_handler_service import DuplicateDelivery, TranscriptionHandlerService
from common.settings import get_settings, get_structured_logger
from common.types import TaskType, WorkerMessage
from worker.healthcheck import HEARTBEAT_DIR, HeartbeatTicker, ensure_heartbeat_dir
from worker.lease_renewer import LeaseRenewer

ray_logger = logging.getLogger("ray")
ray_logger.setLevel(logging.WARNING)
settings = get_settings()

slogger = get_structured_logger()


@ray.remote
class HasBeenStopped:
    def __init__(self):
        self.stopped = False

    def get(self):
        return self.stopped

    def set(self):
        self.stopped = True


# restart indefinitely, try each task only once
@ray.remote(max_restarts=-1, max_task_retries=0)
class RayTranscriptionService:
    def __init__(
        self, transcription_queue_service: QueueService, llm_queue_service: QueueService, stopped: HasBeenStopped
    ) -> None:
        init_sentry()
        self.stopped = stopped
        self.transcription_queue_service = transcription_queue_service
        self.llm_queue_service = llm_queue_service
        actor_id = ray.get_runtime_context().get_actor_id()
        ensure_heartbeat_dir()
        self.heartbeat_path = HEARTBEAT_DIR / f"worker_{actor_id}.heartbeat"
        self.heartbeat_path.touch()
        slogger.debug("Ray Transcription receive service initialised")

    async def process(self) -> None:
        async with HeartbeatTicker(self.heartbeat_path):
            while not await self.stopped.get.remote():
                slogger.debug("Receiving transcription messages")
                messages = await asyncio.to_thread(self.transcription_queue_service.receive_message, max_messages=1)
                for message, receipt_handle in messages:
                    # Keep the message invisible while its (possibly long) task runs, so
                    # it is redelivered only if this worker dies or exceeds the budget.
                    renewer = LeaseRenewer(self.transcription_queue_service, receipt_handle)
                    renewer.start()
                    slogger.refresh_context()
                    slogger.set_context_field("minute_id", str(message.id))
                    ack = True
                    try:
                        try:
                            slogger.info("Received minute id for transcription")
                            transcription_job = await TranscriptionHandlerService.process_transcription(
                                minute_id=message.id,  # message.id -> minute_id
                                async_transcription_message_data=message.data,
                            )
                        except TranscriptionFailedError:
                            slogger.exception("Transcription failed for minute id")
                        else:
                            if transcription_job is None:
                                # Another delivery already owns this job — see reconcile
                                ack = await self._reconcile_duplicate_delivery(message.id)
                            # sync jobs have the transcript immediately, async jobs are re-queued
                            elif transcription_job.transcript:
                                slogger.info("Transcription complete for minute id")
                                minute_version = await MinuteHandlerService.get_only_minute_version_for_minute_id(
                                    message.id
                                )
                                await asyncio.to_thread(
                                    self.llm_queue_service.publish_message,
                                    WorkerMessage(id=minute_version.id, type=TaskType.MINUTE),
                                )
                            else:
                                slogger.info("Async transcription job not ready yet. Re-queueing minute id")
                                await asyncio.to_thread(
                                    self.transcription_queue_service.publish_message,
                                    WorkerMessage(id=message.id, type=TaskType.TRANSCRIPTION, data=transcription_job),
                                )
                    finally:
                        await renewer.stop()
                    if ack:
                        # Delete the message to prevent repeated processing
                        await asyncio.to_thread(self.transcription_queue_service.complete_message, receipt_handle)

    async def _reconcile_duplicate_delivery(self, minute_id: Any) -> bool:
        """Handle a delivery that lost the claim. Returns whether to acknowledge it.

        A job still owned by another worker is left unacknowledged so its delivery can
        still be recovered if that worker dies; a completed job whose minute generation
        message never landed is healed (re-published, idempotent via the minute claim).
        """
        action = TranscriptionHandlerService.reconcile_duplicate_delivery(minute_id)
        if action == DuplicateDelivery.REPUBLISH_MINUTE:
            slogger.info("Healing missing minute generation for completed transcription")
            minute_version = await MinuteHandlerService.get_only_minute_version_for_minute_id(minute_id)
            await asyncio.to_thread(
                self.llm_queue_service.publish_message, WorkerMessage(id=minute_version.id, type=TaskType.MINUTE)
            )
            return True
        if action == DuplicateDelivery.ACK:
            slogger.info("Duplicate delivery acknowledged; job is already terminal")
            return True
        slogger.info("Duplicate delivery left unacknowledged; job is owned by another worker")
        return False


@ray.remote(max_restarts=-1, max_task_retries=0)
class RayLlmService:
    def __init__(self, queue_service: QueueService, stopped: HasBeenStopped) -> None:
        init_sentry()
        self.stopped = stopped
        self.queue_service = queue_service
        actor_id = ray.get_runtime_context().get_actor_id()
        ensure_heartbeat_dir()
        self.heartbeat_path = HEARTBEAT_DIR / f"worker_{actor_id}.heartbeat"
        self.heartbeat_path.touch()
        slogger.info("Ray LLM receive service initialised")

    async def process(self) -> None:
        slogger.debug("Receiving LLM messages from Ray queue")
        async with HeartbeatTicker(self.heartbeat_path):
            while not await self.stopped.get.remote():
                slogger.debug("Receiving LLM messages")
                messages = await asyncio.to_thread(self.queue_service.receive_message, max_messages=10)
                tasks: list[asyncio.Task] = []
                for message, receipt_handle in messages:
                    match message.type:
                        case TaskType.MINUTE:
                            tasks.append(asyncio.create_task(self.process_minute_task(message, receipt_handle)))
                        case TaskType.EDIT:
                            tasks.append(asyncio.create_task(self.process_edit_task(message, receipt_handle)))
                        case _:
                            slogger.warning("Unknown task type: {task_type}", task_type=str(message.type))
                            self.queue_service.deadletter_message(message, receipt_handle)
                if len(tasks) > 0:
                    done, _ = await asyncio.wait(tasks)
                    for task in done:
                        try:
                            task.result()
                        except Exception:
                            slogger.exception("Unhandled error in LLM actor")

    async def process_minute_task(self, message: WorkerMessage, receipt_handle: Any) -> None:
        renewer = LeaseRenewer(self.queue_service, receipt_handle)
        renewer.start()
        slogger.refresh_context()
        slogger.set_context_field("minute_version_id", str(message.id))
        try:
            try:
                slogger.info("Received minute generation message for MinuteVersion")
                disposition = await MinuteHandlerService.process_minute_generation_message(message.id)
                # Delete the message to prevent repeated processing
                slogger.info("Minute generation complete for MinuteVersion")
            except MinuteGenerationFailedError:
                slogger.exception("Minute generation for MinuteVersion failed")
                # For handled errors we complete the message, unhandled errors are not caught
                await asyncio.to_thread(self.queue_service.complete_message, receipt_handle)
            else:
                if disposition == MinuteDelivery.ACK:
                    await asyncio.to_thread(self.queue_service.complete_message, receipt_handle)
        finally:
            await renewer.stop()

    async def process_edit_task(self, message: WorkerMessage, receipt_handle: Any) -> None:
        renewer = LeaseRenewer(self.queue_service, receipt_handle)
        renewer.start()
        slogger.refresh_context()
        slogger.set_context_field("minute_version_id", str(message.id))
        try:
            try:
                slogger.info("Received minute edit message")
                disposition = await MinuteHandlerService.process_minute_edit_message(
                    target_minute_version_id=message.id, source_minute_version_id=message.data.source_id
                )

                slogger.info("Minute edit complete for MinuteVersion")
            except MinuteGenerationFailedError:
                slogger.exception("Minute edit for MinuteVersion failed")
                await asyncio.to_thread(self.queue_service.complete_message, receipt_handle)
            else:
                if disposition == MinuteDelivery.ACK:
                    await asyncio.to_thread(self.queue_service.complete_message, receipt_handle)
        finally:
            await renewer.stop()

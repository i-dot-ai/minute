import asyncio
import logging
from pathlib import Path
from time import monotonic, time

import ray

from common.services.queue_services import get_queue_service
from common.services.queue_services.base import QueueService
from common.settings import get_settings
from worker.healthcheck import HEARTBEAT_DIR, HEARTBEAT_TIMEOUT
from worker.ray_receive_service import HasBeenStopped, RayLlmService, RayTranscriptionService
from worker.signal_handler import SignalHandler

logger = logging.getLogger(__name__)
settings = get_settings()

# How often the supervisor re-stats the actors' heartbeat files. Purely a stat
# throttle: staleness itself is HEARTBEAT_TIMEOUT, so a wedged actor is detected
# at most this long after its window expires — short enough that the local
# watchdog (8 min + 30s) always beats the container healthcheck (~11 min).
STALE_CHECK_INTERVAL_SECONDS = 30


def stale_actor_indices(actors: list, heartbeat_dir: Path, now: float, timeout: int = HEARTBEAT_TIMEOUT) -> list[int]:
    """Indices of actors whose heartbeat file is older than `timeout` seconds.

    Actors whose heartbeat file does not exist yet (still starting up) are skipped —
    the container healthcheck remains the watchdog for wedged startup.
    """
    stale = []
    for idx, actor in enumerate(actors):
        # _actor_id is Ray's only way for the driver to know which heartbeat file an
        # ActorHandle owns (public ActorHandle API has no accessor for it)
        heartbeat_file = heartbeat_dir / f"worker_{actor._actor_id.hex()}.heartbeat"  # noqa: SLF001
        try:
            age = now - heartbeat_file.stat().st_mtime
        except FileNotFoundError:
            continue
        except OSError:
            logger.exception("Failed to stat heartbeat file %s", heartbeat_file)
            continue
        if age > timeout:
            stale.append(idx)
    return stale


class WorkerService:
    def __init__(self, transcription_queue_service: QueueService, llm_queue_service: QueueService):
        self.transcription_queue_service = transcription_queue_service
        self.llm_queue_service = llm_queue_service
        self.actors = []
        self.calls = []
        self.num_transcription_actors = settings.MAX_TRANSCRIPTION_PROCESSES
        self.signal_handler = SignalHandler()
        self.stopped = HasBeenStopped.remote()
        self._last_stale_check = monotonic()
        for _ in range(self.num_transcription_actors):
            self._add_actor(self._create_transcription_actor())
        for _ in range(settings.MAX_LLM_PROCESSES):
            self._add_actor(self._create_llm_actor())

    def _create_transcription_actor(self):
        return RayTranscriptionService.remote(self.transcription_queue_service, self.llm_queue_service, self.stopped)

    def _create_llm_actor(self):
        return RayLlmService.remote(self.llm_queue_service, self.stopped)

    def _add_actor(self, actor) -> None:
        self.actors.append(actor)
        self.calls.append(actor.process.remote())

    def _create_actor(self, idx: int):
        """Create a fresh replacement actor of the same kind as the one at `idx`."""
        if idx < self.num_transcription_actors:
            return self._create_transcription_actor()
        return self._create_llm_actor()

    def _restart_stale_actors(self) -> None:
        stale = stale_actor_indices(self.actors, HEARTBEAT_DIR, now=time())
        for idx in stale:
            try:
                logger.error("Actor %s heartbeat older than %ss — restarting it", self.actors[idx], HEARTBEAT_TIMEOUT)
                old, new = self.actors[idx], self._create_actor(idx)
                # no_restart: the replacement actor is created below; the wedged actor
                # must not resurrect and resume touching its (now-deleted) heartbeat file
                ray.kill(old, no_restart=True)
                Path(HEARTBEAT_DIR / f"worker_{old._actor_id.hex()}.heartbeat").unlink(missing_ok=True)  # noqa: SLF001
                self.actors[idx], self.calls[idx] = new, new.process.remote()
            except Exception:
                logger.exception("Failed to restart stale worker index=%s", idx)

    async def run(self) -> None:
        # note, currently a bug in python 3.12/ray that means we need to wrap the ObjectRefs in asyncio.ensure_future
        futures = [asyncio.ensure_future(call) for call in self.calls]
        while not self.signal_handler.signal_received:
            await self._check_and_restart_tasks(futures)

        logger.info("Signal received. Setting stopped to True")
        await self.stopped.set.remote()

        while True:
            done, pending = await asyncio.wait(futures, timeout=1)
            if not pending:
                logger.info("No remaining jobs. Stopping.")
                break
            logger.info("Waiting for %d jobs", len(pending))

    async def _check_and_restart_tasks(self, futures):
        failed, pending = await asyncio.wait(futures, timeout=1)
        for task in failed:
            # Manually restart failed jobs
            try:
                # exc_info=False as this comes from another process
                logger.error("Task has finished unexpectedly: error %s", task, exc_info=False)
                idx = futures.index(task)
                self.calls[idx] = self.actors[idx].process.remote()
                futures[idx] = asyncio.ensure_future(self.calls[idx])

            except Exception as e:  # noqa: BLE001
                logger.error("Failed to restart worker %s", e)
        if monotonic() - self._last_stale_check >= STALE_CHECK_INTERVAL_SECONDS:
            self._last_stale_check = monotonic()
            self._restart_stale_actors()


def create_worker_service() -> WorkerService:
    settings = get_settings()
    # log the configured providers so it is obvious from the startup logs which services a running worker talks to
    logger.info(
        "Worker configured with transcription services: %s. LLM providers: fast=%s (%s), best=%s (%s)",
        ", ".join(settings.TRANSCRIPTION_SERVICES) or "none",
        settings.FAST_LLM_PROVIDER,
        settings.FAST_LLM_MODEL_NAME,
        settings.BEST_LLM_PROVIDER,
        settings.BEST_LLM_MODEL_NAME,
    )
    transcription_sqs_service = get_queue_service(
        settings.QUEUE_SERVICE_NAME, settings.TRANSCRIPTION_QUEUE_NAME, settings.TRANSCRIPTION_DEADLETTER_QUEUE_NAME
    )
    llm_sqs_service = get_queue_service(
        settings.QUEUE_SERVICE_NAME, settings.LLM_QUEUE_NAME, settings.LLM_DEADLETTER_QUEUE_NAME
    )
    # max concurrent ray processes
    # +4 as we need 2 for the ray Queues, 1 for the HasBeenStopped Actor, plus one 'spare'
    # we init ray here so we can handle its init in testing
    ray.init(
        log_to_driver=True,
        num_cpus=(settings.MAX_TRANSCRIPTION_PROCESSES + settings.MAX_LLM_PROCESSES + 4),
        configure_logging=True,
        dashboard_host=settings.RAY_DASHBOARD_HOST,
        dashboard_port=8265,
        # Setting a logging config stops Ray prefixing forwarded actor logs with "(Actor pid=...)",
        # so structured JSON logs stay valid for CloudWatch.
        logging_config=ray.LoggingConfig(encoding="JSON", log_level="INFO"),
    )
    return WorkerService(transcription_queue_service=transcription_sqs_service, llm_queue_service=llm_sqs_service)

import asyncio
import logging

import ray

from common.logger import setup_logger
from common.services.queue_services import get_queue_service
from common.services.queue_services.base import QueueService
from common.settings import get_settings
from worker.ray_recieve_service import HasBeenStopped, RayLlmService, RayTranscriptionService
from worker.signal_handler import SignalHandler

logger = logging.getLogger(__name__)
settings = get_settings()


class WorkerService:
    def __init__(self, transcription_queue_service: QueueService, llm_queue_service: QueueService):
        self.transcription_queue_service = transcription_queue_service
        self.llm_queue_service = llm_queue_service
        self.actors = []
        self.calls = []
        self.signal_handler = SignalHandler()
        self.stopped = HasBeenStopped.remote()
        for _ in range(settings.MAX_TRANSCRIPTION_PROCESSES):
            transcription_worker = RayTranscriptionService.remote(
                self.transcription_queue_service, self.llm_queue_service, self.stopped
            )
            transcription_worker_call = transcription_worker.process.remote()
            self.actors.append(transcription_worker)
            self.calls.append(transcription_worker_call)

        for _ in range(settings.MAX_LLM_PROCESSES):
            llm_worker = RayLlmService.remote(self.llm_queue_service, self.stopped)
            llm_worker_call = llm_worker.process.remote()
            self.actors.append(llm_worker)
            self.calls.append(llm_worker_call)

    async def run(self) -> None:
        # note, currently a bug in python 3.12/ray that means we need to wrap the ObjectRefs in asyncio.ensure_future
        futures = [asyncio.ensure_future(call) for call in self.calls]
        while not self.signal_handler.signal_received:
            await self._check_and_restart_tasks(futures)

        logger.info("Signal recieved. Setting stopped to True")
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


def create_worker_service() -> WorkerService:
    settings = get_settings()
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
        runtime_env={"worker_process_setup_hook": setup_logger},
    )
    return WorkerService(transcription_queue_service=transcription_sqs_service, llm_queue_service=llm_sqs_service)

import asyncio
import logging

import ray
from ray.util.queue import Queue

from common.logger import setup_logger
from common.services.queue_services import get_queue_service
from common.services.queue_services.base import QueueService
from common.settings import get_settings
from common.types import TaskType
from worker.ray_recieve_service import HasBeenStopped, RayLlmService, RayTranscriptionService
from worker.signal_handler import SignalHandler

logger = logging.getLogger(__name__)
settings = get_settings()


class WorkerService:
    def __init__(self, queue_service: QueueService):
        self.queue_service = queue_service
        self.actors = []
        self.calls = []
        self.signal_handler = SignalHandler()
        self.llm_queue = Queue()
        self.transcription_queue = Queue()
        self.stopped = HasBeenStopped.remote()
        for _ in range(settings.MAX_TRANSCRIPTION_PROCESSES):
            transcription_worker = RayTranscriptionService.remote(
                self.queue_service, self.stopped, self.transcription_queue
            )
            transcription_worker_call = transcription_worker.process.remote()
            self.actors.append(transcription_worker)
            self.calls.append(transcription_worker_call)

        for _ in range(settings.MAX_LLM_PROCESSES):
            llm_worker = RayLlmService.remote(self.queue_service, self.stopped, self.llm_queue)
            llm_worker_call = llm_worker.process.remote()
            self.actors.append(llm_worker)
            self.calls.append(llm_worker_call)

    async def run(self) -> None:
        # note, currently a bug in python 3.12/ray that means we need to wrap the ObjectRefs in asyncio.ensure_future
        futures = [asyncio.ensure_future(call) for call in self.calls]
        while not self.signal_handler.signal_received:
            messages = self.queue_service.receive_message()
            for message, receipt_handle in messages:
                match message.type:
                    case TaskType.TRANSCRIPTION:
                        self.transcription_queue.put((message, receipt_handle))
                    case TaskType.MINUTE | TaskType.EDIT | TaskType.INTERACTIVE:
                        self.llm_queue.put((message, receipt_handle))
                    case _:
                        logger.warning("Message not recognised: %s , Sending to dead letter", message)
                        self.queue_service.deadletter_message(message, receipt_handle)
            await self._check_and_restart_tasks(futures)

        logger.info("Signal recieved. Setting stopped to True")
        await self.stopped.set.remote()

        logger.info("Requeuing messages in Ray queues")
        while not self.transcription_queue.empty():
            _message, receipt_handle = self.transcription_queue.get(block=False)
            self.queue_service.abandon_message(receipt_handle)
        while not self.llm_queue.empty():
            _message, receipt_handle = self.llm_queue.get(block=False)
            self.queue_service.abandon_message(receipt_handle)

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
    sqs_service = get_queue_service(settings.QUEUE_SERVICE_NAME)
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
    return WorkerService(queue_service=sqs_service)

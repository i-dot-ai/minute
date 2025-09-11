import asyncio
import logging

import ray
from ray.util.queue import Empty, Queue

from backend.app.minutes.types import TaskType, WorkerMessage
from backend.services.exceptions import InteractionFailedError, TranscriptionFailedError
from backend.services.minute_handler_service import MinuteGenerationFailedError, MinuteHandlerService
from backend.services.queue_services import get_queue_service
from backend.services.queue_services.base import QueueService
from backend.services.transcription_handler_service import TranscriptionHandlerService
from backend.utils.signal_handler import SignalHandler
from common.logger import setup_logger
from common.settings import get_settings

logger = logging.getLogger(__name__)
ray_logger = logging.getLogger("ray")
ray_logger.setLevel(logging.WARNING)
settings = get_settings()


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
class RayQueueReceiveService:
    def __init__(self, queue_service: QueueService, stopped: HasBeenStopped) -> None:
        self.stopped = stopped
        self.queue_service = queue_service
        logger.info("Ray queue receive service initialised")

    async def process_transcription_task(self, queue: Queue) -> None:
        while True:
            try:
                # if this throws an exception, it should be fatal
                message, receipt_handle = await queue.get_async(block=True, timeout=1)
                try:
                    logger.info("Received minute id for transcription: %s", message.id)
                    transcription_job = await TranscriptionHandlerService.process_transcription(
                        message.id, message.data
                    )
                except TranscriptionFailedError:
                    logger.exception("Transcription failed for minute id: %s", message.id)
                else:
                    # sync jobs should have the transcript available immediately, async jobs may need to go on the queue
                    if transcription_job.transcript:
                        logger.info("Transcription complete for minute id %s complete", message.id)
                        # create a default minute with the general template after every transcription
                        minute_version = await MinuteHandlerService.get_only_minute_version_for_minute_id(message.id)
                        await self.process_minute_task(WorkerMessage(id=minute_version.id, type=TaskType.MINUTE))
                    else:
                        logger.info("Async transcription job not ready yet. Re-queueing minute id: %s", message.id)
                        self.queue_service.publish_message(
                            WorkerMessage(id=message.id, type=TaskType.TRANSCRIPTION, data=transcription_job)
                        )
                # Delete the message to prevent repeated processing
                self.queue_service.complete_message(receipt_handle)
            except Empty:
                if await self.stopped.get.remote():
                    break

    async def process_llm_task(self, queue: Queue) -> None:
        logger.info("receiving LLM messages from Ray queue")
        while True:
            try:
                # if this throws an exception, it should be fatal
                message, receipt_handle = await queue.get_async(block=True, timeout=10)
                try:
                    match message.type:
                        case TaskType.MINUTE:
                            await self.process_minute_task(message)
                        case TaskType.EDIT:
                            await self.process_edit_task(message)
                        case TaskType.INTERACTIVE:
                            await self.process_interactive_task(message)
                        case _:
                            logger.warning("Unknown task type: %s", message.type)
                except Exception:
                    err_message = f"Error processing message {message.id}, {message.type}"
                    logger.exception(err_message)
                # Delete the message to prevent repeated processing
                self.queue_service.complete_message(receipt_handle)
            except Empty:
                if await self.stopped.get.remote():
                    break

    @staticmethod
    async def process_minute_task(message: WorkerMessage) -> None:
        try:
            logger.info("Received minute generation message for MinuteVersion id %s", message.id)

            await MinuteHandlerService.process_minute_generation_message(message.id)

            logger.info("Minute generation complete for MinuteVersion id %s", message.id)
        except MinuteGenerationFailedError:
            logger.exception("Minute generation for MinuteVersion id %s failed", message.id)

    @staticmethod
    async def process_edit_task(message: WorkerMessage) -> None:
        try:
            logger.info("Received minute edit message for minute id %s", message.id)
            await MinuteHandlerService.process_minute_edit_message(
                target_minute_version_id=message.id, source_minute_version_id=message.data.source_id
            )

            logger.info("Minute edit complete for MinuteVersion id %s", message.id)
        except MinuteGenerationFailedError:
            logger.exception("Minute edit for MinuteVersion id %s failed", message.id)

    @staticmethod
    async def process_interactive_task(message: WorkerMessage) -> None:
        try:
            logger.info("Received interactive mode message for chat id %s", message.id)
            await TranscriptionHandlerService.process_interactive_message(message.id)

            logger.info("Interaction complete for chat id %s", message.id)
        except InteractionFailedError:
            logger.exception("Interaction for chat id %s failed", message.id)


class WorkerService:
    def __init__(self, queue_service: QueueService):
        self.queue_service = queue_service
        self.remote_calls = []
        self.signal_handler = SignalHandler()
        self.llm_queue = Queue()
        self.transcription_queue = Queue()
        self.stopped = HasBeenStopped.remote()
        for _ in range(settings.MAX_TRANSCRIPTION_PROCESSES):
            transcription_worker = RayQueueReceiveService.remote(self.queue_service, self.stopped)
            transcription_worker_call = transcription_worker.process_transcription_task.remote(self.transcription_queue)
            self.remote_calls.append(transcription_worker_call)

        for _ in range(settings.MAX_LLM_PROCESSES):
            llm_worker = RayQueueReceiveService.remote(self.queue_service, self.stopped)
            llm_worker_call = llm_worker.process_llm_task.remote(self.llm_queue)
            self.remote_calls.append(llm_worker_call)

    async def run(self) -> None:
        # note, currently a bug in python 3.12/ray that means we need to wrap the ObjectRefs in asyncio.ensure_future
        all_calls_futures = [asyncio.ensure_future(call) for call in self.remote_calls]
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
            failed, pending = await asyncio.wait(all_calls_futures, timeout=1)
            for task in failed:
                # exc_info=False as this comes from another process
                logger.error("Task has finished unexpectedly: error %s", task, exc_info=False)

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
            done, pending = await asyncio.wait(all_calls_futures, timeout=1)
            if not pending:
                logger.info("No remaining jobs. Stopping.")
                break
            logger.info("Waiting for %d jobs", len(pending))


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


if __name__ == "__main__":
    worker_service = create_worker_service()
    asyncio.run(worker_service.run())

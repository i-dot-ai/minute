import logging

import ray
from ray.util.queue import Empty, Queue

from common.services.exceptions import InteractionFailedError, TranscriptionFailedError
from common.services.minute_handler_service import MinuteGenerationFailedError, MinuteHandlerService
from common.services.queue_services.base import QueueService
from common.services.transcription_handler_service import TranscriptionHandlerService
from common.settings import get_settings
from common.types import TaskType, WorkerMessage

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

import asyncio
import logging
from typing import Any

import ray

from common.services.exceptions import InteractionFailedError, TranscriptionFailedError
from common.services.minute_handler_service import MinuteGenerationFailedError, MinuteHandlerService
from common.services.queue_services.base import QueueService
from common.services.transcription_handler_service import TranscriptionHandlerService
from common.settings import get_settings
from common.types import TaskType, WorkerMessage
from worker.healthcheck import HEARTBEAT_DIR

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
class RayTranscriptionService:
    def __init__(
        self, transcription_queue_service: QueueService, llm_queue_service: QueueService, stopped: HasBeenStopped
    ) -> None:
        self.stopped = stopped
        self.transcription_queue_service = transcription_queue_service
        self.llm_queue_service = llm_queue_service
        actor_id = ray.get_runtime_context().get_actor_id()
        self.heartbeat_path = HEARTBEAT_DIR / f"worker_{actor_id}.heartbeat"
        self.heartbeat_path.touch()
        logger.info("Ray Transcription receive service initialised")

    async def process(self) -> None:
        while not await self.stopped.get.remote():
            logger.info("Receiving transcription messages")
            messages = self.transcription_queue_service.receive_message(max_messages=1)
            for message, receipt_handle in messages:
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
                        self.llm_queue_service.publish_message(
                            WorkerMessage(id=minute_version.id, type=TaskType.MINUTE)
                        )
                    else:
                        logger.info("Async transcription job not ready yet. Re-queueing minute id: %s", message.id)
                        self.transcription_queue_service.publish_message(
                            WorkerMessage(id=message.id, type=TaskType.TRANSCRIPTION, data=transcription_job)
                        )
                # Delete the message to prevent repeated processing
                self.transcription_queue_service.complete_message(receipt_handle)
            self.heartbeat_path.touch()


@ray.remote(max_restarts=-1, max_task_retries=0)
class RayLlmService:
    def __init__(self, queue_service: QueueService, stopped: HasBeenStopped) -> None:
        self.stopped = stopped
        self.queue_service = queue_service
        actor_id = ray.get_runtime_context().get_actor_id()
        self.heartbeat_path = HEARTBEAT_DIR / f"worker_{actor_id}.heartbeat"
        self.heartbeat_path.touch()
        logger.info("Ray LLM receive service initialised")

    async def process(self) -> None:
        logger.info("receiving LLM messages from Ray queue")
        while not await self.stopped.get.remote():
            logger.info("Receiving LLM messages")
            messages = self.queue_service.receive_message(max_messages=10)
            tasks: list[asyncio.Task] = []
            for message, receipt_handle in messages:
                match message.type:
                    case TaskType.MINUTE:
                        tasks.append(asyncio.create_task(self.process_minute_task(message, receipt_handle)))
                    case TaskType.EDIT:
                        tasks.append(asyncio.create_task(self.process_edit_task(message, receipt_handle)))
                    case TaskType.INTERACTIVE:
                        tasks.append(asyncio.create_task(self.process_interactive_task(message, receipt_handle)))
                    case _:
                        logger.warning("Unknown task type: %s", message.type)
                        self.queue_service.deadletter_message(message, receipt_handle)
            if len(tasks) > 0:
                done, pending = await asyncio.wait(tasks)
                for task in done:
                    try:
                        task.result()
                    except Exception:
                        logger.exception("Unhandled error in LLM actor")

            self.heartbeat_path.touch()

    async def process_minute_task(self, message: WorkerMessage, receipt_handle: Any) -> None:
        try:
            logger.info("Received minute generation message for MinuteVersion id %s", message.id)

            await MinuteHandlerService.process_minute_generation_message(message.id)
            # Delete the message to prevent repeated processing
            logger.info("Minute generation complete for MinuteVersion id %s", message.id)
        except MinuteGenerationFailedError:
            logger.exception("Minute generation for MinuteVersion id %s failed", message.id)
            # For handled errors we complete the message, unhandled errors are not caught
            self.queue_service.complete_message(receipt_handle)
        else:
            # If no error then complete the message
            self.queue_service.complete_message(receipt_handle)

    async def process_edit_task(self, message: WorkerMessage, receipt_handle: Any) -> None:
        try:
            logger.info("Received minute edit message for minute id %s", message.id)
            await MinuteHandlerService.process_minute_edit_message(
                target_minute_version_id=message.id, source_minute_version_id=message.data.source_id
            )

            logger.info("Minute edit complete for MinuteVersion id %s", message.id)
        except MinuteGenerationFailedError:
            logger.exception("Minute edit for MinuteVersion id %s failed", message.id)
            self.queue_service.complete_message(receipt_handle=receipt_handle)
        else:
            self.queue_service.complete_message(receipt_handle=receipt_handle)

    async def process_interactive_task(self, message: WorkerMessage, receipt_handle: Any) -> None:
        try:
            logger.info("Received interactive mode message for chat id %s", message.id)
            await TranscriptionHandlerService.process_interactive_message(message.id)
            logger.info("Interaction complete for chat id %s", message.id)
        except InteractionFailedError:
            logger.exception("Interaction for chat id %s failed", message.id)
            self.queue_service.complete_message(receipt_handle=receipt_handle)
        else:
            self.queue_service.complete_message(receipt_handle=receipt_handle)

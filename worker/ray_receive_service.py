import asyncio
import logging
from typing import Any

import ray

from common.sentry import init_sentry
from common.services.exceptions import InteractionFailedError, TranscriptionFailedError
from common.services.queue_services.base import QueueService
from common.settings import get_settings, get_structured_logger
from common.types import TaskType, WorkerMessage
from worker.healthcheck import HEARTBEAT_DIR, ensure_heartbeat_dir

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
        from common.services.minute_handler_service import MinuteHandlerService
        from common.services.transcription_handler_service import TranscriptionHandlerService

        while not await self.stopped.get.remote():
            slogger.debug("Receiving transcription messages")
            messages = self.transcription_queue_service.receive_message(max_messages=1)
            for message, receipt_handle in messages:
                slogger.refresh_context()
                slogger.set_context_field("minute_id", str(message.id))
                try:
                    slogger.info("Received minute id for transcription")
                    transcription_job = await TranscriptionHandlerService.process_transcription(
                        minute_id=message.id,  # message.id -> minute_id
                        async_transcription_message_data=message.data,
                    )
                except TranscriptionFailedError:
                    slogger.exception("Transcription failed for minute id")
                else:
                    # sync jobs should have the transcript available immediately, async jobs may need to go on the queue
                    if transcription_job.transcript:
                        slogger.info("Transcription complete for minute id")
                        # create a default minute with the general template after every transcription
                        minute_version = await MinuteHandlerService.get_only_minute_version_for_minute_id(message.id)
                        self.llm_queue_service.publish_message(
                            WorkerMessage(id=minute_version.id, type=TaskType.MINUTE)
                        )
                    else:
                        slogger.info("Async transcription job not ready yet. Re-queueing minute id")
                        self.transcription_queue_service.publish_message(
                            WorkerMessage(id=message.id, type=TaskType.TRANSCRIPTION, data=transcription_job)
                        )
                # Delete the message to prevent repeated processing
                self.transcription_queue_service.complete_message(receipt_handle)
            self.heartbeat_path.touch()


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
        while not await self.stopped.get.remote():
            slogger.debug("Receiving LLM messages")
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
                        slogger.warning("Unknown task type: {task_type}", task_type=str(message.type))
                        self.queue_service.deadletter_message(message, receipt_handle)
            if len(tasks) > 0:
                done, _ = await asyncio.wait(tasks)
                for task in done:
                    try:
                        task.result()
                    except Exception:
                        slogger.exception("Unhandled error in LLM actor")

            self.heartbeat_path.touch()

    async def process_minute_task(self, message: WorkerMessage, receipt_handle: Any) -> None:
        from common.services.minute_handler_service import MinuteGenerationFailedError, MinuteHandlerService

        slogger.refresh_context()
        slogger.set_context_field("minute_version_id", str(message.id))
        try:
            slogger.info("Received minute generation message for MinuteVersion")
            await MinuteHandlerService.process_minute_generation_message(message.id)
            # Delete the message to prevent repeated processing
            slogger.info("Minute generation complete for MinuteVersion")
        except MinuteGenerationFailedError:
            slogger.exception("Minute generation for MinuteVersion failed")
            # For handled errors we complete the message, unhandled errors are not caught
            self.queue_service.complete_message(receipt_handle)
        else:
            # If no error then complete the message
            self.queue_service.complete_message(receipt_handle)

    async def process_edit_task(self, message: WorkerMessage, receipt_handle: Any) -> None:
        from common.services.minute_handler_service import MinuteGenerationFailedError, MinuteHandlerService

        slogger.refresh_context()
        slogger.set_context_field("minute_version_id", str(message.id))
        try:
            slogger.info("Received minute edit message")
            await MinuteHandlerService.process_minute_edit_message(
                target_minute_version_id=message.id, source_minute_version_id=message.data.source_id
            )

            slogger.info("Minute edit complete for MinuteVersion")
        except MinuteGenerationFailedError:
            slogger.exception("Minute edit for MinuteVersion failed")
            self.queue_service.complete_message(receipt_handle=receipt_handle)
        else:
            self.queue_service.complete_message(receipt_handle=receipt_handle)

    async def process_interactive_task(self, message: WorkerMessage, receipt_handle: Any) -> None:
        from common.services.transcription_handler_service import TranscriptionHandlerService

        slogger.refresh_context()
        slogger.set_context_field("chat_id", str(message.id))
        try:
            slogger.info("Received interactive mode message")
            await TranscriptionHandlerService.process_interactive_message(message.id)
            slogger.info("Interaction complete")
        except InteractionFailedError:
            slogger.exception("Interaction failed")
            self.queue_service.complete_message(receipt_handle=receipt_handle)
        else:
            self.queue_service.complete_message(receipt_handle=receipt_handle)

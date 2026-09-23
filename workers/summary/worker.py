import logging

from common.services.exceptions import InteractionFailedError
from common.services.interactive_chat_service import process_interactive_message
from common.services.queue_services.sqs import SQSQueueService
from common.types import EditMessageData, TaskType, WorkerMessage
from workers.base_worker import BaseWorker, PoisonMessageError
from workers.signal_handler import SignalHandler
from workers.summary.minute_handler_service import MinuteGenerationFailedError, MinuteHandlerService

logger = logging.getLogger(__name__)

# One prompt per task. Total concurrency across the fleet equals the number of running
# LLM worker tasks, so scaling is controlled entirely by ECS (desired count / autoscaling)
# rather than multiplied by an in-process batch size. This lets us run many tiny tasks
# and keep precise control over the total number of concurrent LLM calls.
MAX_CONCURRENT_LLM_TASKS = 1


class SummaryWorker(BaseWorker):
    """I/O-bound worker that handles LLM tasks (minute generation, edits, interactive chat).

    Processes a single message at a time; horizontal scaling is delegated to ECS.
    """

    max_messages = MAX_CONCURRENT_LLM_TASKS

    def __init__(self, llm_queue_service: SQSQueueService, signal_handler: SignalHandler | None = None):
        super().__init__(llm_queue_service, signal_handler)
        self.llm_queue_service = llm_queue_service

    async def process_message(self, message: WorkerMessage) -> None:
        """Route an LLM task to its handler.

        Domain failures (e.g. MinuteGenerationFailedError) already persist a FAILED
        state in the database, so they are treated as handled and the message is
        completed. Unexpected errors propagate to the base worker for retry.
        """
        match message.type:
            case TaskType.MINUTE:
                await self._process_minute_task(message)
            case TaskType.EDIT:
                await self._process_edit_task(message)
            case TaskType.INTERACTIVE:
                await self._process_interactive_task(message)
            case _:
                msg = f"Unknown task type: {message.type}"
                raise PoisonMessageError(msg)

    async def _process_minute_task(self, message: WorkerMessage) -> None:
        try:
            logger.info("Received minute generation message for MinuteVersion id %s", message.id)
            await MinuteHandlerService.process_minute_generation_message(message.id)
            logger.info("Minute generation complete for MinuteVersion id %s", message.id)
        except MinuteGenerationFailedError:
            logger.exception("Minute generation for MinuteVersion id %s failed", message.id)

    async def _process_edit_task(self, message: WorkerMessage) -> None:
        logger.info("Received minute edit message for minute id %s", message.id)

        if not isinstance(message.data, EditMessageData):
            msg = f"Invalid data for edit task {message.id}: {type(message.data)}"
            raise PoisonMessageError(msg)

        try:
            await MinuteHandlerService.process_minute_edit_message(
                target_minute_version_id=message.id,
                source_minute_version_id=message.data.source_id,
            )
            logger.info("Minute edit complete for MinuteVersion id %s", message.id)
        except MinuteGenerationFailedError:
            logger.exception("Minute edit for MinuteVersion id %s failed", message.id)

    async def _process_interactive_task(self, message: WorkerMessage) -> None:
        try:
            logger.info("Received interactive mode message for chat id %s", message.id)
            await process_interactive_message(message.id)
            logger.info("Interaction complete for chat id %s", message.id)
        except InteractionFailedError:
            logger.exception("Interaction for chat id %s failed", message.id)

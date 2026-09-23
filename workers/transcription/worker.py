import logging

from common.services.exceptions import TranscriptionFailedError
from common.services.queue_services.sqs import SQSQueueService
from common.types import TaskType, TranscriptionJobMessageData, WorkerMessage
from workers.base_worker import BaseWorker
from workers.signal_handler import SignalHandler
from workers.transcription.handler import TranscriptionHandlerService

logger = logging.getLogger(__name__)

# Seconds to wait before re-checking an async transcription job that is not ready yet.
# Avoids a tight busy-loop hammering the transcription provider and SQS.
ASYNC_RECHECK_DELAY_SECONDS = 30

# Bound concurrency so we do not hold too many large audio files in memory at once
# (the synchronous adapter reads the whole file into RAM).
MAX_CONCURRENT_TRANSCRIPTIONS = 3


class TranscriptionWorker(BaseWorker):
    """I/O-bound worker that handles transcription API calls.

    Reads preprocessed audio jobs from the transcription-ready queue and, on success,
    publishes a minute-generation job to the LLM queue.
    """

    max_messages = MAX_CONCURRENT_TRANSCRIPTIONS

    def __init__(
        self,
        transcription_ready_queue_service: SQSQueueService,
        llm_queue_service: SQSQueueService,
        signal_handler: SignalHandler | None = None,
    ):
        super().__init__(transcription_ready_queue_service, signal_handler)
        self.transcription_ready_queue_service = transcription_ready_queue_service
        self.llm_queue_service = llm_queue_service

    async def process_message(self, message: WorkerMessage) -> None:
        """Process a transcription job."""
        logger.info("Processing transcription for minute id: %s", message.id)

        transcription_data = message.data if isinstance(message.data, TranscriptionJobMessageData) else None

        try:
            transcription_job = await TranscriptionHandlerService.process_transcription(
                minute_id=message.id,
                async_transcription_message_data=transcription_data,
            )
        except TranscriptionFailedError:
            # process_transcription already marked the Transcription FAILED and captured
            # the error. Treat as handled: complete the message so we do not retry a
            # deterministic failure.
            logger.exception("Transcription failed for minute id: %s", message.id)
            return

        if transcription_job.transcript:
            logger.info("Transcription complete for minute id: %s", message.id)
            from common.services.minute_handler_service import MinuteHandlerService

            minute_version = await MinuteHandlerService.get_only_minute_version_for_minute_id(message.id)
            self.llm_queue_service.publish_message(WorkerMessage(id=minute_version.id, type=TaskType.MINUTE))
        else:
            logger.info(
                "Async transcription job not ready yet. Re-queueing minute id %s in %ds",
                message.id,
                ASYNC_RECHECK_DELAY_SECONDS,
            )
            self.transcription_ready_queue_service.publish_message(
                WorkerMessage(id=message.id, type=TaskType.TRANSCRIPTION, data=transcription_job),
                delay_seconds=ASYNC_RECHECK_DELAY_SECONDS,
            )

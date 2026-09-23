import logging
from uuid import UUID

from sqlalchemy.orm import selectinload

from common.audio.speakers import process_speakers_and_dialogue_entries
from common.database.postgres_database import SessionLocal
from common.database.postgres_models import JobStatus, Minute, Transcription
from common.generate_meeting_title import generate_meeting_title
from common.services.exceptions import TranscriptionFailedError
from common.services.posthog_client import capture_event
from common.services.transcription_status import update_transcription
from common.types import DialogueEntry, TranscriptionJobMessageData
from workers.transcription.services.transcription_manager import TranscriptionServiceManager

transcription_manager = TranscriptionServiceManager()
logger = logging.getLogger(__name__)


class TranscriptionHandlerService:
    """Orchestrates a transcription job: DB lifecycle, speaker ID, title, analytics."""

    @classmethod
    def get_transcription_from_minute_id(cls, minute_id: UUID) -> Transcription:
        with SessionLocal() as session:
            minute = session.get(
                Minute,
                minute_id,
                options=[selectinload(Minute.transcription).selectinload(Transcription.recordings)],
            )
            if not minute:
                msg = f"minute id {minute_id} not found"
                raise ValueError(msg)
            if not minute.transcription:
                msg = f"minute id {minute_id} has no transcription!"
                raise ValueError(msg)

            transcription = minute.transcription
            session.expunge(transcription)
            return transcription

    @classmethod
    async def process_transcription(
        cls, minute_id: UUID, async_transcription_message_data: TranscriptionJobMessageData | None = None
    ) -> TranscriptionJobMessageData:
        """Process a transcription job and save results.

        Returns the job with `transcript` populated when complete, or without a
        transcript when an async job is still running (so the caller re-queues).
        """
        try:
            transcription = cls.get_transcription_from_minute_id(minute_id)
        except Exception as e:
            raise TranscriptionFailedError from e

        try:
            if async_transcription_message_data:
                transcription_job = await transcription_manager.check_transcription(
                    adapter_name=async_transcription_message_data.transcription_service,
                    async_transcription_message_data=async_transcription_message_data,
                )
            else:
                # it's a new transcription job
                update_transcription(transcription.id, status=JobStatus.IN_PROGRESS)
                transcription_job = await transcription_manager.perform_transcription_steps(transcription=transcription)

            if transcription_job.transcript:
                dialogue_entries = await cls.identify_speakers(transcription_job.transcript)
                meeting_title = await generate_meeting_title(transcript=dialogue_entries)
                update_transcription(
                    transcription.id, status=JobStatus.COMPLETED, transcript=dialogue_entries, title=meeting_title
                )
                capture_event(
                    transcription.user_id,
                    "transcription_succeeded",
                    {"transcriptionId": str(transcription.id)},
                )

        except Exception as e:
            msg = f"Transcription failed: {e!s}"
            logger.exception(msg)
            try:
                update_transcription(transcription.id, status=JobStatus.FAILED, error=msg)
            except Exception:
                logger.exception("Error updating transcription status. Maybe it doesn't exist?")

            capture_event(
                transcription.user_id,
                "transcription_failed",
                {"transcriptionId": str(transcription.id)},
            )
            raise TranscriptionFailedError from e
        else:
            return transcription_job

    @classmethod
    async def identify_speakers(cls, dialogue_entries: list[DialogueEntry]) -> list[DialogueEntry]:
        try:
            dialogue_entries = await process_speakers_and_dialogue_entries(dialogue_entries)
        except Exception:
            # Do not break flow if this step fails
            logger.exception("Error processing dialogue entries")
        return dialogue_entries

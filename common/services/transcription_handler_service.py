from datetime import datetime
from enum import StrEnum, auto
from uuid import UUID

from sqlalchemy import update
from sqlalchemy.orm import selectinload
from sqlmodel import select

from common.audio.speakers import process_speakers_and_dialogue_entries
from common.database.postgres_database import SessionLocal
from common.database.postgres_models import JobStatus, Minute, MinuteVersion, Transcription
from common.generate_meeting_title import generate_meeting_title
from common.services.exceptions import TranscriptionFailedError
from common.services.job_claim import JobClaimRenewer, claim_job, refresh_job
from common.services.posthog_client import capture_event
from common.services.storage_services import get_storage_service
from common.services.transcription_services.transcription_manager import TranscriptionServiceManager
from common.settings import get_settings, get_structured_logger
from common.types import DialogueEntry, TranscriptionJobMessageData

settings = get_settings()
transcription_manager = TranscriptionServiceManager()
storage_service = get_storage_service(settings.STORAGE_SERVICE_NAME)
slogger = get_structured_logger()


class DuplicateDelivery(StrEnum):
    """What a delivery should do when another worker already owns the claim."""

    ACK = auto()  # job is already terminal: safe to delete this delivery
    LEAVE = auto()  # job is owned by a live worker: keep the delivery for recovery
    REPUBLISH_MINUTE = auto()  # completed, but its minute generation message is missing


class TranscriptionHandlerService:
    @classmethod
    def get_transcription(cls, transcription_id: UUID) -> Transcription:
        with SessionLocal() as session:
            transcription = session.exec(
                select(Transcription)
                .where(Transcription.id == transcription_id)
                .options(selectinload(Transcription.recordings))
            ).first()
            if transcription is None:
                msg = f"transcription id {transcription_id} not found"
                raise ValueError(msg)
            if not transcription.recordings:
                msg = f"transcription id {transcription_id} has no recording!"
                raise ValueError(msg)

            session.expunge(transcription)
            return transcription

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
    def update_transcription(
        cls,
        transcription_id: UUID,
        claim_token: datetime,
        status: JobStatus | None = None,
        transcript: list[DialogueEntry] | None = None,
        title: str | None = None,
        error: str | None = None,
    ) -> bool:
        """Update a transcription only while claim_token still owns it.

        The update is applied only if the row still carries the claim token, so a
        superseded worker's late write is dropped instead of clobbering the new owner.
        Returns whether the write was applied.

        updated_datetime IS the claim token, so nothing else may write a processing
        row (see the 409 guard in PATCH /transcriptions/{id}).
        """
        values: dict = {}
        if status is not None:
            values["status"] = status
        if transcript:
            values["dialogue_entries"] = transcript
        if error:
            values["error"] = error
        if title:
            values["title"] = title
        with SessionLocal() as session:
            result = session.exec(
                update(Transcription)
                .where(Transcription.id == transcription_id, Transcription.updated_datetime == claim_token)
                .values(**values)
            )
            session.commit()
            return result.rowcount == 1

    @staticmethod
    def claim_transcription(transcription_id: UUID) -> datetime | None:
        return claim_job(Transcription, transcription_id)

    @classmethod
    def reconcile_duplicate_delivery(cls, minute_id: UUID) -> DuplicateDelivery:
        """Decide what a delivery should do when it could not claim the job.

        A delivery loses the claim when another worker owns it (duplicate/redelivery).
        The right action depends on the job's state, not this delivery's: acknowledging a
        job that is still IN_PROGRESS risks deleting the only delivery needed for
        recovery, while a COMPLETED job whose minute generation message never landed
        (crash or failed publish in between) must be healed on redelivery.
        """
        try:
            transcription = cls.get_transcription_from_minute_id(minute_id)
        except Exception:
            slogger.exception("Could not load transcription to reconcile a duplicate delivery")
            return DuplicateDelivery.LEAVE

        if transcription.status == JobStatus.FAILED:
            return DuplicateDelivery.ACK
        if transcription.status != JobStatus.COMPLETED:
            return DuplicateDelivery.LEAVE

        with SessionLocal() as session:
            versions = session.exec(
                select(MinuteVersion)
                .join(Minute, Minute.id == MinuteVersion.minute_id)
                .where(Minute.transcription_id == transcription.id)
            ).all()
        if len(versions) == 1 and versions[0].status == JobStatus.AWAITING_START:
            return DuplicateDelivery.REPUBLISH_MINUTE
        return DuplicateDelivery.ACK

    @classmethod
    async def process_transcription(  # noqa: C901
        cls,
        minute_id: UUID,
        async_transcription_message_data: TranscriptionJobMessageData | None = None,
    ) -> TranscriptionJobMessageData | None:
        """Process a transcription job and save results. Returns None if another delivery already owns this job."""
        slogger.set_context_field("minute_id", str(minute_id))
        try:
            transcription = cls.get_transcription_from_minute_id(minute_id)
            slogger.set_context_field("transcription_id", str(transcription.id))
            slogger.set_context_field("user_id", str(transcription.user_id))
        except Exception as e:
            raise TranscriptionFailedError from e

        message_token = async_transcription_message_data.claim_token if async_transcription_message_data else None
        claim_token = refresh_job(Transcription, transcription.id, message_token) if message_token else None
        if claim_token is None:
            # A poll whose token was superseded (e.g. its worker crashed after rotating it)
            # may still take over abandoned work, but never a fresh AWAITING_START job.
            claim_token = claim_job(Transcription, transcription.id, include_awaiting=message_token is None)
        if claim_token is None:
            return None
        renewer = JobClaimRenewer(Transcription, transcription.id, claim_token)
        try:
            async with renewer:
                if async_transcription_message_data:
                    transcription_job = await transcription_manager.check_transcription(
                        adapter_name=async_transcription_message_data.transcription_service,
                        async_transcription_message_data=async_transcription_message_data,
                    )
                else:
                    transcription_job = await transcription_manager.perform_transcription_steps(
                        transcription=transcription
                    )
                if transcription_job.transcript:
                    dialogue_entries = await cls.identify_speakers(transcription_job.transcript)
                    meeting_title = await generate_meeting_title(transcript=dialogue_entries)
            claim_token = renewer.token
            transcription_job.claim_token = claim_token

            if transcription_job.transcript:
                applied = cls.update_transcription(
                    transcription.id,
                    status=JobStatus.COMPLETED,
                    transcript=dialogue_entries,
                    title=meeting_title,
                    claim_token=claim_token,
                )
                if not applied:
                    slogger.warning("Transcription claim was superseded; result discarded")
                    return None
                await cls.delete_provider_output(transcription_job.transcript_key)
                capture_event(
                    transcription.user_id, "transcription_succeeded", {"transcriptionId": str(transcription.id)}
                )
        except Exception as e:
            msg = f"Transcription failed: {e!s}"
            if not cls.update_transcription(
                transcription.id, status=JobStatus.FAILED, error=msg, claim_token=renewer.token
            ):
                return None
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
            slogger.exception("Error processing dialogue entries")
        return dialogue_entries

    @classmethod
    async def delete_provider_output(cls, key: str | None) -> None:
        """Best-effort removal of the provider's transcript object once it is persisted.

        Must never raise: it runs after the COMPLETED write, and an exception would be
        caught by process_transcription and overwrite the row as FAILED.
        """
        if not key:
            return
        try:
            await storage_service.delete(key)
        except Exception:
            # ponytail: logged only; add an S3 lifecycle rule on restricted/transcribe-output/ if these show up
            slogger.exception("Failed to delete provider transcript output")

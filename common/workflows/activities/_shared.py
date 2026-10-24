"""Helpers shared by the transcription activities: the row, its claim and fenced writes."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import update
from sqlmodel import col

from common.database.postgres_database import SessionLocal
from common.database.postgres_models import JobStatus, Transcription
from common.services.exceptions import TranscriptionFailedError
from common.services.job_claim import claim_job
from common.services.posthog_client import capture_event
from common.services.transcription_handler_service import TranscriptionHandlerService
from common.settings import get_structured_logger


class TranscriptionTransientError(Exception):
    """The attempt lost its claim or its write could not be applied; retry without touching the row."""


# Statuses a step may write to: IN_PROGRESS while the workflow runs, COMPLETED for the
# post-completion steps (title). Never AWAITING_START (a retry reset) or FAILED.
WRITABLE_STATUSES = (JobStatus.IN_PROGRESS, JobStatus.COMPLETED)

slogger = get_structured_logger()


def load(minute_id: UUID) -> Transcription:
    """The minute's transcription with its recordings. Raises TranscriptionFailedError if it is gone."""
    slogger.set_context_field("minute_id", str(minute_id))
    try:
        transcription = TranscriptionHandlerService.get_transcription_from_minute_id(minute_id)
    except Exception as e:
        raise TranscriptionFailedError from e
    slogger.set_context_field("transcription_id", str(transcription.id))
    slogger.set_context_field("user_id", str(transcription.user_id))
    return transcription


def get_row(transcription_id: UUID) -> Transcription | None:
    try:
        return TranscriptionHandlerService.get_transcription(transcription_id)
    except ValueError:
        return None


def update_in_progress(transcription_id: UUID, **values) -> bool:
    """Write to the row only while it is IN_PROGRESS. Returns whether it was applied."""
    with SessionLocal() as session:
        result = session.exec(
            update(Transcription)
            .where(col(Transcription.id) == transcription_id, col(Transcription.status) == JobStatus.IN_PROGRESS)
            .values(**values)
        )
        session.commit()
        return result.rowcount == 1  # pyright: ignore[reportAttributeAccessIssue]


def update_when_writable(transcription_id: UUID, **values) -> bool:
    """Write while the row is IN_PROGRESS or COMPLETED (post-completion steps). Returns whether it was applied."""
    with SessionLocal() as session:
        result = session.exec(
            update(Transcription)
            .where(col(Transcription.id) == transcription_id, col(Transcription.status).in_(WRITABLE_STATUSES))
            .values(**values)
        )
        session.commit()
        return result.rowcount == 1  # pyright: ignore[reportAttributeAccessIssue]


def in_progress(transcription_id: UUID) -> Transcription | None:
    """The row if a step may still write to it; None if it was deleted, failed or finished."""
    row = get_row(transcription_id)
    if row is None or row.status != JobStatus.IN_PROGRESS:
        slogger.info("Transcription no longer in progress; skipping step")
        return None
    return row


def take_claim(transcription: Transcription) -> datetime:
    """This attempt's fencing token.

    An IN_PROGRESS row is ours (Temporal runs one attempt at a time and one workflow per
    transcription, so it is this workflow's own earlier attempt); an AWAITING_START row is
    claimed. Raises TranscriptionTransientError if the row moved between the read and the claim.
    """
    if transcription.status == JobStatus.IN_PROGRESS:
        return transcription.updated_datetime
    token = claim_job(Transcription, transcription.id)
    if token is None:
        msg = "Transcription changed while being claimed; retrying"
        raise TranscriptionTransientError(msg)
    return token


def fenced_update(transcription_id: UUID, claim_token: datetime, **values) -> bool:
    """Apply only while claim_token still owns the row, so a superseded attempt's late write is dropped."""
    return TranscriptionHandlerService.update_transcription(transcription_id, claim_token, **values)


def mark_failed(transcription: Transcription, claim_token: datetime, error: Exception) -> str | None:
    """Mark the row FAILED if this attempt still owns it. Returns the message, or None if superseded."""
    msg = f"Transcription failed: {error!s}"
    if not fenced_update(transcription.id, claim_token, status=JobStatus.FAILED, error=msg):
        return None
    capture_event(transcription.user_id, "transcription_failed", {"transcriptionId": str(transcription.id)})
    return msg

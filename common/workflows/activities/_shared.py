"""Helpers shared by the transcription activities: the row and its status-guarded writes."""

from uuid import UUID

from sqlalchemy import or_, update
from sqlmodel import col

from common.database.postgres_database import SessionLocal
from common.database.postgres_models import JobStatus, Transcription
from common.services.exceptions import TranscriptionFailedError
from common.services.posthog_client import capture_event
from common.services.transcription_handler_service import TranscriptionHandlerService
from common.settings import get_structured_logger


class TranscriptionTransientError(Exception):
    """Retryable: a dependency blip or the row moved on before the write; retry without touching it."""


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


def set_title_if_empty(transcription_id: UUID, title: str) -> bool:
    """Write a generated title only while the row is writable and still has none, so a title the
    user set after completion is never overwritten. Returns whether it was applied."""
    with SessionLocal() as session:
        result = session.exec(
            update(Transcription)
            .where(
                col(Transcription.id) == transcription_id,
                col(Transcription.status).in_(WRITABLE_STATUSES),
                or_(col(Transcription.title).is_(None), col(Transcription.title) == ""),
            )
            .values(title=title)
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


def mark_failed(transcription: Transcription, error: Exception) -> str | None:
    """Mark the row FAILED while it is still processing. Returns the message, or None if it moved on."""
    msg = f"Transcription failed: {error!s}"
    if not update_in_progress(transcription.id, status=JobStatus.FAILED, error=msg):
        return None
    capture_event(transcription.user_id, "transcription_failed", {"transcriptionId": str(transcription.id)})
    return msg

"""Helpers shared by the transcription activities: the row and its status-guarded writes."""

from uuid import UUID

from sqlalchemy import ColumnElement, case, literal, or_, update
from sqlmodel import col, func

from common.database.postgres_database import SessionLocal
from common.database.postgres_models import JobStatus, Transcription
from common.services.exceptions import TranscriptionFailedError
from common.services.posthog_client import capture_event
from common.services.transcription_handler_service import TranscriptionHandlerService
from common.settings import get_structured_logger


class TranscriptionTransientError(Exception):
    """Retryable: a dependency blip or the row moved on before the write; retry without touching it."""


slogger = get_structured_logger()


def load(minute_id: UUID) -> Transcription:
    """The minute's transcription with its recordings. Raises TranscriptionFailedError if it is gone."""
    slogger.set_context_field("minute_id", str(minute_id))
    try:
        transcription = TranscriptionHandlerService.get_transcription_from_minute_id(minute_id)
    except ValueError as e:
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


def set_generated_title_and_keywords(transcription: Transcription, title: str, keywords: list[str]) -> bool:
    """Fill missing metadata only; a supplied title or explicitly empty keyword list is preserved."""
    title_column = col(Transcription.title)
    keywords_column = col(Transcription.search_keywords)
    keywords_missing = keywords_column.is_(None)
    missing = keywords_missing
    values: dict[str, ColumnElement] = {
        "search_keywords": func.coalesce(keywords_column, literal(keywords, type_=keywords_column.type)),
        "search_keywords_generated": or_(keywords_missing, col(Transcription.search_keywords_generated)),
    }
    if title:
        title_missing = or_(title_column.is_(None), title_column == "")
        missing = or_(missing, title_missing)
        values["title"] = case((title_missing, title), else_=title_column)

    with SessionLocal() as session:
        result = session.exec(
            update(Transcription)
            .where(
                col(Transcription.id) == transcription.id,
                col(Transcription.status) == JobStatus.IN_PROGRESS,
                # A retry resets created_datetime, so a late result cannot enrich the next attempt.
                col(Transcription.created_datetime) == transcription.created_datetime,
                missing,
            )
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


def mark_failed(transcription: Transcription, error: Exception | str) -> str | None:
    """Finalise unfinished work, including a failure before the initial claim; preserve terminal rows."""
    msg = f"Transcription failed: {error!s}"
    with SessionLocal() as session:
        result = session.exec(
            update(Transcription)
            .where(
                col(Transcription.id) == transcription.id,
                col(Transcription.status).in_((JobStatus.AWAITING_START, JobStatus.IN_PROGRESS)),
            )
            .values(status=JobStatus.FAILED, error=msg)
        )
        session.commit()
        if result.rowcount != 1:  # pyright: ignore[reportAttributeAccessIssue]
            return None
    capture_event(transcription.user_id, "transcription_failed", {"transcriptionId": str(transcription.id)})
    return msg

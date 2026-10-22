"""Helpers shared by the transcription activities: the row and its claim.

Code used by a single activity lives in that activity's module; this holds what several need.
"""

from datetime import datetime
from uuid import UUID

from sqlalchemy import update
from sqlmodel import col

from common.database.postgres_database import AsyncSessionLocal
from common.database.postgres_models import Transcription
from common.database.repository import get_transcription, get_transcription_for_minute, update_in_progress_transcription
from common.services.job_claim import claim_job
from common.services.posthog_client import capture_event
from common.services.stt import TranscriptionFailedError, TranscriptionTransientError
from common.settings import get_structured_logger
from common.types import JobStatus

slogger = get_structured_logger()


async def load(minute_id: UUID) -> Transcription:
    """The minute's transcription with its recordings. Raises TranscriptionFailedError if it is gone."""
    slogger.set_context_field("minute_id", str(minute_id))
    try:
        async with AsyncSessionLocal() as session:
            transcription = await get_transcription_for_minute(session, minute_id)
    except Exception as e:
        raise TranscriptionFailedError from e
    slogger.set_context_field("transcription_id", str(transcription.id))
    slogger.set_context_field("user_id", str(transcription.user_id))
    return transcription


async def get_row(transcription_id: UUID) -> Transcription | None:
    async with AsyncSessionLocal() as session:
        return await get_transcription(session, transcription_id)


async def update_in_progress(transcription_id: UUID, **values) -> bool:
    """Write to the row only while it is IN_PROGRESS. Returns whether it was applied."""
    async with AsyncSessionLocal() as session:
        applied = await update_in_progress_transcription(session, transcription_id, **values)
        await session.commit()
        return applied


async def in_progress(transcription_id: UUID) -> Transcription | None:
    """The row if a step may still write to it; None if it was deleted, failed or finished."""
    row = await get_row(transcription_id)
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


async def fenced_update(transcription_id: UUID, claim_token: datetime, **values) -> bool:
    """Apply only while claim_token still owns the row, so a superseded attempt's late write is dropped."""
    async with AsyncSessionLocal() as session:
        result = await session.exec(
            update(Transcription)
            .where(col(Transcription.id) == transcription_id, col(Transcription.updated_datetime) == claim_token)
            .values(**values)
        )
        await session.commit()
        return result.rowcount == 1  # pyright: ignore[reportAttributeAccessIssue]


async def mark_failed(transcription: Transcription, claim_token: datetime, error: Exception) -> str | None:
    """Mark the row FAILED if this attempt still owns it. Returns the message, or None if superseded."""
    msg = f"Transcription failed: {error!s}"
    if not await fenced_update(transcription.id, claim_token, status=JobStatus.FAILED, error=msg):
        return None
    capture_event(transcription.user_id, "transcription_failed", {"transcriptionId": str(transcription.id)})
    return msg

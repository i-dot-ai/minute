from datetime import datetime, timedelta
from typing import cast
from uuid import UUID

from sqlalchemy import CursorResult, and_, update
from sqlalchemy.orm import selectinload
from sqlmodel import col, func, null, select
from sqlmodel.ext.asyncio.session import AsyncSession

from common.database.postgres_models import Minute, MinuteVersion, Transcription, User
from common.types import DialogueEntry, JobStatus


async def get_transcription(session: AsyncSession, transcription_id: UUID) -> Transcription | None:
    return await session.get(Transcription, transcription_id)


async def get_transcription_with_recordings(session: AsyncSession, transcription_id: UUID) -> Transcription:
    transcription = (
        await session.exec(
            select(Transcription)
            .where(col(Transcription.id) == transcription_id)
            .options(selectinload(Transcription.recordings))
        )
    ).first()
    if not transcription:
        msg = f"transcription id {transcription_id} not found"
        raise ValueError(msg)
    return transcription


async def get_transcription_for_minute(session: AsyncSession, minute_id: UUID) -> Transcription:
    """The minute's transcription with its recordings (newest first) eager-loaded."""
    minute = await session.get(
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
    return minute.transcription


async def update_in_progress_transcription(session: AsyncSession, transcription_id: UUID, **values) -> bool:
    """Write only while the row is still IN_PROGRESS (not deleted, failed or completed).

    The status guard makes post-processing writes no-ops once the user deleted the row or
    another path finished it. Returns whether the row was updated.
    """
    result = cast(
        CursorResult,
        await session.exec(
            update(Transcription)
            .where(col(Transcription.id) == transcription_id, col(Transcription.status) == JobStatus.IN_PROGRESS)
            .values(**values)
        ),
    )
    return result.rowcount == 1


async def mark_transcription_completed(
    session: AsyncSession, transcription_id: UUID, transcript: list[DialogueEntry], title: str
) -> None:
    await session.exec(
        update(Transcription)
        .where(col(Transcription.id) == transcription_id)
        .values(dialogue_entries=transcript, title=title, status=JobStatus.COMPLETED, error=None)
    )


async def mark_transcription_failed(session: AsyncSession, transcription_id: UUID, error: str) -> None:
    await session.exec(
        update(Transcription)
        .where(col(Transcription.id) == transcription_id)
        .values(status=JobStatus.FAILED, error=error)
    )


async def reset_transcription_for_retry(session: AsyncSession, transcription_id: UUID) -> None:
    await session.exec(
        update(Transcription)
        .where(col(Transcription.id) == transcription_id)
        .values(status=JobStatus.AWAITING_START, error=None, dialogue_entries=None)
    )


async def find_expired_transcriptions(session: AsyncSession) -> list[Transcription]:
    """Transcriptions older than their owner's data retention period."""
    statement = (
        select(Transcription)
        .join(User, col(User.id) == col(Transcription.user_id))
        .where(
            col(User.data_retention_days).is_not(null()),
            col(Transcription.created_datetime) < func.now() - col(User.data_retention_days) * timedelta(days=1),
        )
    )
    return list((await session.exec(statement)).all())


async def finalize_stale_in_progress(
    session: AsyncSession, model: type[Transcription] | type[MinuteVersion], created_before: datetime, error: str
) -> int:
    """Mark rows stuck IN_PROGRESS since before `created_before` as FAILED, so users can retry.

    ponytail: keyed on created_datetime (no lease column without a schema change); B's
    finalize_stale_* on claimed_at is the precise version.
    """
    result = cast(
        CursorResult,
        await session.exec(
            update(model)
            .where(and_(col(model.created_datetime) < created_before, col(model.status) == JobStatus.IN_PROGRESS))
            .values(status=JobStatus.FAILED, error=error)
        ),
    )
    return result.rowcount

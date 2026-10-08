from uuid import UUID

from sqlalchemy import update
from sqlalchemy.orm import selectinload
from sqlmodel import col, select
from sqlmodel.ext.asyncio.session import AsyncSession

from common.database.postgres_models import JobStatus, Minute, MinuteVersion, Transcription
from common.database.repository.shared import ClaimState, claim_for_processing, make_finalizer


async def get_version_with_transcription(session: AsyncSession, minute_version_id: UUID) -> MinuteVersion:
    """Eager-load version -> minute -> transcription (+ recordings) so the detached
    object graph survives the session closing."""
    version = (
        await session.exec(
            select(MinuteVersion)
            .where(col(MinuteVersion.id) == minute_version_id)
            .options(
                selectinload(MinuteVersion.minute)
                .selectinload(Minute.transcription)
                .selectinload(Transcription.recordings)
            )
        )
    ).first()
    if not version:
        msg = f"MinuteVersion not found for id: {minute_version_id}"
        raise ValueError(msg)
    return version


async def claim_version_for_processing(
    session: AsyncSession, minute_version_id: UUID, stale_seconds: int
) -> ClaimState:
    return await claim_for_processing(session, MinuteVersion, minute_version_id, stale_seconds)


async def mark_version_completed(session: AsyncSession, minute_version_id: UUID, html_content: str) -> None:
    await session.execute(
        update(MinuteVersion)
        .where(col(MinuteVersion.id) == minute_version_id)
        .values(html_content=html_content, status=JobStatus.COMPLETED, error=None)
    )


async def mark_version_failed(session: AsyncSession, minute_version_id: UUID, error: str) -> None:
    await session.execute(
        update(MinuteVersion)
        .where(col(MinuteVersion.id) == minute_version_id)
        .values(status=JobStatus.FAILED, error=error)
    )


async def reset_version_for_retry(session: AsyncSession, minute_version_id: UUID) -> None:
    await session.execute(
        update(MinuteVersion)
        .where(col(MinuteVersion.id) == minute_version_id)
        .values(status=JobStatus.AWAITING_START, error=None, html_content="", claimed_at=None)
    )


finalize_stale_versions = make_finalizer(MinuteVersion, "Unknown error. Job finalised by cleanup process")

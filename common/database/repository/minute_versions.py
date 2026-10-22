from uuid import UUID

from sqlalchemy import update
from sqlalchemy.orm import selectinload
from sqlmodel import col, select
from sqlmodel.ext.asyncio.session import AsyncSession

from common.database.postgres_models import Minute, MinuteVersion, Transcription
from common.types import JobStatus


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


async def get_only_version_for_minute(session: AsyncSession, minute_id: UUID) -> MinuteVersion:
    """The minute's single version. Only valid for initial generation (exactly one version)."""
    minute = await session.get(Minute, minute_id, options=[selectinload(Minute.minute_versions)])
    if not minute:
        msg = f"Minute not found for minute id: {minute_id}"
        raise ValueError(msg)
    if not minute.minute_versions:
        msg = f"MinuteVersion not found for minute id: {minute_id}"
        raise ValueError(msg)
    if len(minute.minute_versions) != 1:
        msg = (
            f"More than one MinuteVersions found for minute id: {minute_id}. This function should only be "
            f"used for the initial generation of a Minute."
        )
        raise ValueError(msg)
    return minute.minute_versions[0]


async def mark_version_completed(session: AsyncSession, minute_version_id: UUID, html_content: str) -> None:
    await session.exec(
        update(MinuteVersion)
        .where(col(MinuteVersion.id) == minute_version_id)
        .values(html_content=html_content, status=JobStatus.COMPLETED, error=None)
    )


async def mark_version_failed(session: AsyncSession, minute_version_id: UUID, error: str) -> None:
    await session.exec(
        update(MinuteVersion)
        .where(col(MinuteVersion.id) == minute_version_id)
        .values(status=JobStatus.FAILED, error=error)
    )


async def reset_version_for_retry(session: AsyncSession, minute_version_id: UUID) -> None:
    await session.exec(
        update(MinuteVersion)
        .where(col(MinuteVersion.id) == minute_version_id)
        .values(status=JobStatus.AWAITING_START, error=None, html_content="")
    )

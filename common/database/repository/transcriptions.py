from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import update
from sqlalchemy.orm import selectinload
from sqlmodel import col, select
from sqlmodel.ext.asyncio.session import AsyncSession

from common.database.postgres_models import JobStatus, Transcription
from common.database.repository.shared import ClaimState, claim_for_processing, make_finalizer

if TYPE_CHECKING:
    from common.types import DialogueEntry


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


async def claim_transcription_for_processing(
    session: AsyncSession, transcription_id: UUID, stale_seconds: int
) -> ClaimState:
    return await claim_for_processing(session, Transcription, transcription_id, stale_seconds)


async def mark_transcription_completed(
    session: AsyncSession,
    transcription_id: UUID,
    transcript: list["DialogueEntry"],
    title: str,
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
        .values(status=JobStatus.AWAITING_START, error=None, dialogue_entries=None, claimed_at=None)
    )


finalize_stale_transcriptions = make_finalizer(Transcription, "Unknown error. Job finalised by cleanup process")

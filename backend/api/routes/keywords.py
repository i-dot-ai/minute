import uuid

from fastapi import APIRouter, HTTPException, Response
from sqlmodel.ext.asyncio.session import AsyncSession

from backend.api.dependencies import SQLSessionDep, UserDep
from common.database.postgres_models import Transcription
from common.types import TranscriptionKeywords

from .transcriptions import _transcription_for_edit

keywords_router = APIRouter(prefix="/transcriptions/{transcription_id}/keywords", tags=["Transcriptions"])


@keywords_router.get("")
async def list_transcription_keywords(
    transcription_id: uuid.UUID, session: SQLSessionDep, current_user: UserDep, response: Response
) -> TranscriptionKeywords:
    """List the search keywords for a transcription owned by the current user."""
    transcription = await session.get(Transcription, transcription_id)
    if not transcription or transcription.user_id != current_user.id:
        raise HTTPException(404, detail="Transcription not found")
    response.headers["Cache-Control"] = "private, no-store"
    return TranscriptionKeywords(keywords=transcription.search_keywords or [])


async def _save_transcription_keywords(
    transcription_id: uuid.UUID, keywords: list[str], session: AsyncSession, user_id: uuid.UUID
) -> None:
    transcription = await _transcription_for_edit(transcription_id, session, user_id)
    transcription.search_keywords = keywords
    transcription.search_keywords_generated = False
    await session.commit()


@keywords_router.put("")
async def replace_transcription_keywords(
    transcription_id: uuid.UUID, request: TranscriptionKeywords, session: SQLSessionDep, current_user: UserDep
) -> TranscriptionKeywords:
    """Create or replace the entire keyword list."""
    await _save_transcription_keywords(transcription_id, request.keywords, session, current_user.id)
    return request


@keywords_router.delete("", status_code=204)
async def delete_transcription_keywords(
    transcription_id: uuid.UUID, session: SQLSessionDep, current_user: UserDep
) -> None:
    """Clear the keyword list."""
    await _save_transcription_keywords(transcription_id, [], session, current_user.id)

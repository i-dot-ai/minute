import uuid

from fastapi import HTTPException, status
from sqlalchemy.orm import selectinload
from sqlmodel import select

from backend.api.dependencies import SQLSessionDep, UserDep
from common.database.postgres_models import Minute
from common.types import MinuteVersionResponse


async def endpoint(
    user: UserDep,
    session: SQLSessionDep,
    minute_id: uuid.UUID,
) -> list[MinuteVersionResponse]:
    """List all versions of a minute, ensuring the minute belongs to the current user."""

    result = await session.exec(
        select(Minute)
        .where(Minute.id == minute_id)
        .options(
            selectinload(Minute.minute_versions),
            selectinload(Minute.transcription),
        )
    )
    minute = result.first()
    if not minute or not minute.transcription.user_id or (minute.transcription.user_id != user.id):
        msg = f"Minute {minute_id} not found for user {user.id}"
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=msg)

    return [
        MinuteVersionResponse(
            id=version.id,
            minute_id=minute_id,
            status=version.status,
            created_datetime=version.created_datetime,
            updated_datetime=version.updated_datetime,
            error=version.error,
            ai_edit_instructions=version.ai_edit_instructions,
            html_content=version.html_content,
            content_source=version.content_source,
        )
        for version in minute.minute_versions
    ]

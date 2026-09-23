import uuid

from fastapi import HTTPException, status
from sqlmodel import col, select

from backend.api.dependencies import SQLSessionDep, UserDep
from common.database.postgres_models import Minute, Transcription
from common.types import MinuteListItem


async def endpoint(
    user: UserDep,
    session: SQLSessionDep,
    transcription_id: uuid.UUID,
) -> list[MinuteListItem]:
    """List all minutes for a given transcription, ensuring the transcription belongs to the current user."""

    transcription = await session.get(Transcription, transcription_id)
    if not transcription or transcription.user_id != user.id:
        msg = f"Transcription {transcription_id} not found for user {user.id}"
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=msg)

    query = (
        select(Minute)
        .where(Minute.transcription_id == transcription_id)
        .order_by(col(Minute.updated_datetime).desc())
    )
    result = await session.exec(query)
    minutes = result.all()

    return [
        MinuteListItem(
            id=minute.id,
            created_datetime=minute.created_datetime,
            updated_datetime=minute.updated_datetime,
            transcription_id=minute.transcription_id,
            template_name=minute.template_name,
            agenda=minute.agenda,
        )
        for minute in minutes
    ]

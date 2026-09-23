import uuid

from fastapi import HTTPException, status
from sqlalchemy.orm import selectinload
from sqlmodel import select

from backend.api.dependencies import SQLSessionDep, UserDep
from common.database.postgres_models import Minute, MinuteVersion


async def endpoint(
    user: UserDep,
    session: SQLSessionDep,
    minute_version_id: uuid.UUID,
) -> None:
    """Delete a minute version by its ID, ensuring it belongs to the current user."""

    query = (
        select(MinuteVersion)
        .where(MinuteVersion.id == minute_version_id)
        .options(selectinload(MinuteVersion.minute).selectinload(Minute.transcription))
    )

    result = await session.exec(query)
    minute_version = result.first()

    if (
        not minute_version
        or not minute_version.minute.transcription.user_id
        or minute_version.minute.transcription.user_id != user.id
    ):
        msg = f"Minute version {minute_version_id} not found for user {user.id}"
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=msg)

    await session.delete(minute_version)
    await session.commit()

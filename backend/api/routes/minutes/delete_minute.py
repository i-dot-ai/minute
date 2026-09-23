import uuid

from fastapi import HTTPException, status
from sqlalchemy.orm import selectinload
from sqlmodel import select

from backend.api.dependencies import SQLSessionDep, UserDep
from common.database.postgres_models import Minute


async def endpoint(
    user: UserDep,
    session: SQLSessionDep,
    minute_id: uuid.UUID,
) -> None:
    """Delete a minute by its ID, ensuring it belongs to the current user."""

    query = (
        select(Minute)
        .where(Minute.id == minute_id)
        .options(selectinload(Minute.transcription))
    )

    result = await session.exec(query)
    minute = result.first()

    if not minute or not minute.transcription.user_id or (minute.transcription.user_id != user.id):
        msg = f"Minute {minute_id} not found for user {user.id}"
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=msg)

    await session.delete(minute)
    await session.commit()

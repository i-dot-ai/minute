from uuid import UUID

from fastapi import HTTPException, status
from sqlmodel import select

from backend.api.dependencies import UserDep
from backend.api.dependencies.get_session import SQLSessionDep
from common.database.postgres_models import UserTemplate


async def endpoint(
        user: UserDep,
        session: SQLSessionDep,
        template_id: UUID,
) -> None:
    """Delete a user template for the current user."""

    template = (
        await session.exec(
            select(UserTemplate)
            .where(
                UserTemplate.id == template_id,
                UserTemplate.user_id == user.id,
        ))
    ).first()

    if not template:
        msg = f"User template {template_id} not found for user {user.id}"
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=msg)

    await session.delete(template)
    await session.commit()

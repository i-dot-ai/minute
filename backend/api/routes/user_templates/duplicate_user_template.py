from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.orm import selectinload
from sqlmodel import select

from backend.api.dependencies import UserDep
from backend.api.dependencies.get_session import SQLSessionDep
from common.database.postgres_models import TemplateQuestion, UserTemplate


async def endpoint(
    user: UserDep,
    session: SQLSessionDep,
    template_id: UUID,
) -> UUID:
    """Duplicate a user template for the current user."""

    original_template = (
        await session.exec(
            select(UserTemplate)
            .where(
                UserTemplate.id == template_id,
                UserTemplate.user_id == user.id,
            )
            .options(selectinload(UserTemplate.questions)) # pyright: ignore[reportArgumentType]
        )
    ).first()

    if not original_template:
        msg = f"User template {template_id} not found for user {user.id}"
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=msg)

    template = UserTemplate(
        user_id=user.id,
        name=original_template.name + " (Copy)",
        description=original_template.description,
        content=original_template.content,
        type=original_template.type,
        questions=[
            TemplateQuestion(
                position=question.position,
                title=question.title,
                description=question.description,
            ) # pyright: ignore[reportCallIssue]
            for question in original_template.questions
        ],
    )

    session.add(template)
    await session.commit()

    return template.id

from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.orm import selectinload
from sqlmodel import select

from backend.api.dependencies import UserDep
from backend.api.dependencies.get_session import SQLSessionDep
from common.database.postgres_models import TemplateType, UserTemplate
from common.types import Question, TemplateResponse


async def endpoint(
    user: UserDep,
    session: SQLSessionDep,
    template_id: UUID,
) -> TemplateResponse:
    """Get a user template by its ID, ensuring it belongs to the current user."""

    template = (
        await session.exec(
            select(UserTemplate)
            .where(
                UserTemplate.id == template_id,
                UserTemplate.user_id == user.id,
            )
            .options(selectinload(UserTemplate.questions))  # pyright: ignore[reportArgumentType]
        )
    ).first()

    if not template:
        msg = f"User template not found: {template_id}"
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=msg)

    if template.type == TemplateType.DOCUMENT:
        questions = None
    elif template.type == TemplateType.FORM:
        questions = [
            Question(
                id=question.id,
                title=question.title,
                description=question.description,
                position=question.position,
            )
            for question in template.questions
        ]
    else:
        msg = f"Template type not found: {template.type}"
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=msg)

    return TemplateResponse(
        id=template.id,
        name=template.name,
        updated_datetime=template.updated_datetime,
        content=template.content,
        description=template.description,
        type=template.type,
        questions=questions,
        is_default=template.id == user.default_template_id,
    )

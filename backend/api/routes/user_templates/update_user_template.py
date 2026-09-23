import datetime
from uuid import UUID

from fastapi import HTTPException
from sqlmodel import select

from backend.api.dependencies import UserDep
from backend.api.dependencies.get_session import SQLSessionDep
from common.database.postgres_models import TemplateQuestion, UserTemplate
from common.types import PatchUserTemplateRequest, Question


async def endpoint(
    user: UserDep,
    session: SQLSessionDep,
    req: PatchUserTemplateRequest,
    template_id: UUID,
) -> None:
    """Update a user template by its ID, ensuring it belongs to the current user."""

    template = (
        await session.exec(
            select(UserTemplate).where(
                UserTemplate.id == template_id,
                UserTemplate.user_id == user.id,
            )
        )
    ).first()

    if not template:
        raise HTTPException(404)

    if req.name is not None:
        template.name = req.name
    if req.content is not None:
        template.content = req.content
    if req.description is not None:
        template.description = req.description
    if req.questions is not None:
        questions = list(
            (await session.exec(select(TemplateQuestion).where(TemplateQuestion.user_template_id == template_id))).all()
        )
        for question in req.questions:
            if isinstance(question, Question):
                existing_idx = next((i for i, q in enumerate(questions) if q.id == question.id), None)
                if existing_idx:
                    existing = questions.pop(existing_idx)
                    existing.title = question.title
                    existing.description = question.description
                    existing.position = question.position
                    continue

            session.add(
                TemplateQuestion(
                    user_template_id=template_id,
                    position=question.position,
                    title=question.title,
                    description=question.description,
                )
            )
        for remaining_question in questions:
            await session.delete(remaining_question)

    # Touched explicitly: a questions-only PATCH changes only TemplateQuestion rows, so
    # the column's onupdate never fires for user_template.
    template.updated_datetime = datetime.datetime.now(tz=datetime.UTC)

    await session.commit()

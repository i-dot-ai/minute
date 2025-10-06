import datetime
from uuid import UUID

from fastapi import APIRouter, HTTPException
from sqlalchemy.orm import selectinload
from sqlmodel import col, select

from backend.api.dependencies import UserDep
from backend.api.dependencies.get_session import SQLSessionDep
from common.database.postgres_models import TemplateQuestion, TemplateType, UserTemplate
from common.services.template_manager import TemplateManager
from common.settings import get_settings
from common.types import (
    CreateUserTemplateRequest,
    PatchUserTemplateRequest,
    Question,
    TemplateMetadata,
    TemplateResponse,
)

templates_router = APIRouter(tags=["Templates"])
all_template_metadata = TemplateManager.get_template_metadata()
beta_templates = get_settings().BETA_TEMPLATE_NAMES
ga_only_template_metadata = [template for template in all_template_metadata if template.name not in beta_templates]


@templates_router.get("/templates")
def get_templates(user: UserDep) -> list[TemplateMetadata]:  # noqa: ARG001
    """Get metadata for all templates."""
    # currently we have no beta templates. Uncomment this code to enable this feature
    # if posthog_client and posthog_client.get_feature_flag("beta-templates", user.email):
    #     return all_template_metadata
    # else:
    #     return ga_only_template_metadata
    return ga_only_template_metadata


@templates_router.get("/user-templates")
async def get_user_templates(user: UserDep, session: SQLSessionDep) -> list[TemplateResponse]:
    templates = (
        await session.exec(
            select(UserTemplate)
            .where(UserTemplate.user_id == user.id)
            .order_by(col(UserTemplate.updated_datetime).desc())
        )
    ).all()

    return [
        TemplateResponse(
            id=template.id,
            updated_datetime=template.updated_datetime,
            name=template.name,
            content=template.content,
            description=template.description,
            type=template.type,
            questions=None,
        )
        for template in templates
    ]


@templates_router.get("/user-templates/{template_id}")
async def get_user_template(user: UserDep, session: SQLSessionDep, template_id: UUID) -> TemplateResponse:
    template = (
        await session.exec(
            select(UserTemplate)
            .where(UserTemplate.id == template_id, UserTemplate.user_id == user.id)
            .options(selectinload(UserTemplate.questions))
        )
    ).first()

    if not template:
        raise HTTPException(404)

    return TemplateResponse(
        id=template.id,
        name=template.name,
        updated_datetime=template.updated_datetime,
        content=template.content,
        description=template.description,
        type=template.type,
        questions=None
        if template.type == TemplateType.DOCUMENT
        else [
            Question(id=question.id, title=question.title, description=question.description, position=question.position)
            for question in template.questions
        ],
    )


@templates_router.post("/user-templates")
async def create_user_template(user: UserDep, session: SQLSessionDep, request: CreateUserTemplateRequest) -> None:
    template = UserTemplate(
        name=request.name,
        content=request.content,
        description=request.description,
        user_id=user.id,
        type=request.type,
        questions=[
            TemplateQuestion(
                position=question.position,
                title=question.title,
                description=question.description,
            )  # type: ignore  # noqa: PGH003
            for question in (request.questions or [])
        ],
    )

    session.add(template)
    await session.commit()


@templates_router.patch("/user-templates/{template_id}")
async def edit_user_template(
    user: UserDep, session: SQLSessionDep, template_id: UUID, request: PatchUserTemplateRequest
) -> None:
    template = (
        await session.exec(select(UserTemplate).where(UserTemplate.id == template_id, UserTemplate.user_id == user.id))
    ).first()

    if not template:
        raise HTTPException(404)

    if request.name is not None:
        template.name = request.name
    if request.content is not None:
        template.content = request.content
    if request.description is not None:
        template.description = request.description
    if request.questions is not None:
        questions = list(
            (await session.exec(select(TemplateQuestion).where(TemplateQuestion.user_template_id == template_id))).all()
        )
        for question in request.questions:
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

    template.updated_datetime = datetime.datetime.now(tz=datetime.UTC)

    await session.commit()


@templates_router.delete("/user-templates/{template_id}")
async def delete_user_template(user: UserDep, session: SQLSessionDep, template_id: UUID) -> None:
    template = (
        await session.exec(select(UserTemplate).where(UserTemplate.id == template_id, UserTemplate.user_id == user.id))
    ).first()

    if not template:
        raise HTTPException(404)

    await session.delete(template)
    await session.commit()


@templates_router.post("/user-templates/{template_id}/duplicate")
async def duplicate_user_template(user: UserDep, session: SQLSessionDep, template_id: UUID) -> None:
    original_template = (
        await session.exec(
            select(UserTemplate)
            .where(UserTemplate.id == template_id, UserTemplate.user_id == user.id)
            .options(selectinload(UserTemplate.questions))
        )
    ).first()

    if not original_template:
        raise HTTPException(404)

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
            )  # type: ignore  # noqa: PGH003
            for question in original_template.questions
        ],
    )

    session.add(template)
    await session.commit()

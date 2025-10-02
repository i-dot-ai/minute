import datetime
from collections.abc import Sequence
from uuid import UUID

from fastapi import APIRouter, HTTPException
from sqlmodel import col, select

from backend.api.dependencies import UserDep
from backend.api.dependencies.get_session import SQLSessionDep
from common.database.postgres_models import UserTemplate
from common.services.template_manager import TemplateManager
from common.settings import get_settings
from common.types import (
    CreateUserTemplateRequest,
    PatchUserTemplateRequest,
    TemplateMetadata,
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
async def get_user_templates(user: UserDep, session: SQLSessionDep) -> Sequence[UserTemplate]:
    return (
        await session.exec(
            select(UserTemplate)
            .where(UserTemplate.user_id == user.id)
            .order_by(col(UserTemplate.updated_datetime).desc())
        )
    ).all()


@templates_router.get("/user-templates/{template_id}")
async def get_user_template(user: UserDep, session: SQLSessionDep, template_id: UUID) -> UserTemplate:
    template = (
        await session.exec(select(UserTemplate).where(UserTemplate.id == template_id, UserTemplate.user_id == user.id))
    ).first()

    if not template:
        raise HTTPException(404)

    return template


@templates_router.post("/user-templates")
async def create_user_template(
    user: UserDep, session: SQLSessionDep, request: CreateUserTemplateRequest
) -> UserTemplate:
    template = UserTemplate(
        name=request.name, content=request.content, description=request.description, user_id=user.id
    )
    session.add(template)
    await session.commit()
    await session.refresh(template)
    return template


@templates_router.patch("/user-templates/{template_id}")
async def edit_user_template(
    user: UserDep, session: SQLSessionDep, template_id: UUID, request: PatchUserTemplateRequest
) -> UserTemplate:
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

    template.updated_datetime = datetime.datetime.now(tz=datetime.UTC)

    await session.commit()

    return template


@templates_router.delete("/user-templates/{template_id}")
async def delete_user_template(user: UserDep, session: SQLSessionDep, template_id: UUID):
    template = (
        await session.exec(select(UserTemplate).where(UserTemplate.id == template_id, UserTemplate.user_id == user.id))
    ).first()

    if not template:
        raise HTTPException(404)

    await session.delete(template)
    await session.commit()


@templates_router.post("/user-templates/{template_id}/duplicate")
async def duplicate_user_template(user: UserDep, session: SQLSessionDep, template_id: UUID) -> UserTemplate:
    template = (
        await session.exec(select(UserTemplate).where(UserTemplate.id == template_id, UserTemplate.user_id == user.id))
    ).first()

    if not template:
        raise HTTPException(404)

    new_template = UserTemplate(
        user_id=user.id, name=template.name + " (Copy)", description=template.description, content=template.content
    )

    session.add(new_template)
    await session.commit()
    await session.refresh(new_template)

    return new_template

from fastapi import APIRouter, HTTPException
from sqlmodel import select

from backend.api.dependencies import SQLSessionDep, UserDep
from common.database.postgres_models import User, UserTemplate
from common.services.template_manager import TemplateManager
from common.services.user_details import display_name_from_email, has_fixed_data_retention
from common.settings import get_settings, get_structured_logger
from common.types import (
    DataRetentionUpdateResponse,
    GetUserResponse,
    SetDefaultLanguageRequest,
    SetDefaultTemplateRequest,
    SetDisplayNameRequest,
)

users_router = APIRouter(tags=["Users"])

logger = get_structured_logger()


def _user_response(user: User) -> GetUserResponse:
    return GetUserResponse(
        id=user.id,
        created_datetime=user.created_datetime,
        updated_datetime=user.updated_datetime,
        email=user.email,
        display_name=user.display_name or display_name_from_email(user.email),
        data_retention_days=user.data_retention_days,
        default_template_id=user.default_template_id,
        default_template_name=user.default_template_name,
        default_language=user.default_language,
    )


@users_router.get("/users/me")
def get_user(user: UserDep) -> GetUserResponse:
    return _user_response(user)


@users_router.patch("/users/display-name", response_model=GetUserResponse)
async def update_display_name(
    data: SetDisplayNameRequest,
    session: SQLSessionDep,
    user: UserDep,
) -> GetUserResponse:
    """Set or clear the current user's display name.

    Args:
        data: Request body containing display_name; null clears it, omitting the field leaves it unchanged.
        session: Database session
        user: The current authenticated user
    """
    if "display_name" not in data.model_fields_set:
        return _user_response(user)

    stripped = data.display_name.strip() if data.display_name else ""
    if data.display_name is not None and not stripped:
        raise HTTPException(status_code=400, detail="Display name cannot be blank")

    user.display_name = stripped or None
    await session.commit()
    await session.refresh(user)

    logger.info(
        "{action} display name",
        action="Cleared" if data.display_name is None else "Updated",
    )
    return _user_response(user)


@users_router.patch("/users/data-retention", response_model=GetUserResponse)
async def update_data_retention(
    data: DataRetentionUpdateResponse,
    session: SQLSessionDep,
    user: UserDep,
) -> GetUserResponse:
    """Update the data retention period for the current user.

    Args:
        data: Request body containing data_retention_days
        current_user: The current authenticated user
    """
    if has_fixed_data_retention(user.email):
        raise HTTPException(
            status_code=403,
            detail="Data retention for your department is fixed and cannot be changed",
        )

    if data.data_retention_days is not None and data.data_retention_days < 1:
        raise HTTPException(
            status_code=400,
            detail="Data retention period must be at least 1 day or None for indefinite retention",
        )

    user.data_retention_days = data.data_retention_days

    await session.commit()
    await session.refresh(user)

    logger.info("Updated data retention period to {days} days", days=data.data_retention_days)

    return _user_response(user)


@users_router.patch("/users/default-language", response_model=GetUserResponse)
async def update_default_language(
    data: SetDefaultLanguageRequest,
    session: SQLSessionDep,
    user: UserDep,
) -> GetUserResponse:
    """Set or clear the current user's default summary language; null means English."""
    user.default_language = data.default_language

    await session.commit()
    await session.refresh(user)

    logger.info("Updated default language to {language}", language=data.default_language)

    return _user_response(user)


@users_router.patch("/users/default-template", response_model=GetUserResponse)
async def update_default_template(
    data: SetDefaultTemplateRequest,
    session: SQLSessionDep,
    user: UserDep,
) -> GetUserResponse:
    """Set the current user's default template.

    Exactly one of template_id (a custom template owned by the user) or template_name (a
    system template) may be provided. Providing neither clears the default. Setting a new
    default overwrites the previous one, so there is only ever one default per user.
    """
    if data.template_id is not None and data.template_name is not None:
        raise HTTPException(status_code=400, detail="Provide either template_id or template_name, not both")

    if data.template_id is not None:
        template = (
            await session.exec(
                select(UserTemplate).where(UserTemplate.id == data.template_id, UserTemplate.user_id == user.id)
            )
        ).first()
        if not template:
            raise HTTPException(404, detail="User template not found")
        user.default_template_id = template.id
        user.default_template_name = None
    elif data.template_name is not None:
        valid_names = {
            template.name
            for template in TemplateManager.get_template_metadata()
            if template.name not in get_settings().BETA_TEMPLATE_NAMES
        }
        if data.template_name not in valid_names:
            raise HTTPException(404, detail="System template not found")
        user.default_template_name = data.template_name
        user.default_template_id = None
    else:
        user.default_template_id = None
        user.default_template_name = None

    await session.commit()
    await session.refresh(user)

    logger.info("Updated default template")

    return _user_response(user)

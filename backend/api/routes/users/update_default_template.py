import logging

from fastapi import HTTPException, status
from sqlmodel import select

from backend.api.dependencies import SQLSessionDep, UserDep
from common.database.postgres_models import UserTemplate
from common.services import system_template_manager
from common.settings import get_settings
from common.types import GetUserResponse, SetDefaultTemplateRequest

logger = logging.getLogger(__name__)


async def endpoint(
    user: UserDep,
    session: SQLSessionDep,
    req: SetDefaultTemplateRequest,
) -> GetUserResponse:
    """Set the current user's default template.

    Exactly one of template_id (a custom template owned by the user) or template_name (a
    system template) may be provided. Providing neither clears the default. Setting a new
    default overwrites the previous one, so there is only ever one default per user.
    """

    # --- User template
    if req.template_id is not None:
        template = (
            await session.exec(
                select(UserTemplate).where(
                    UserTemplate.id == req.template_id,
                    UserTemplate.user_id == user.id,
                )
            )
        ).first()
        if not template:
            msg = f"User template not found: {req.template_id}"
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=msg)
        user.default_template_id = template.id
        user.default_template_name = None

    # --- System template
    elif req.template_name is not None:
        valid_names = {
            template.name
            for template in system_template_manager.get_template_metadata()
            if template.name not in get_settings().BETA_TEMPLATE_NAMES
        }
        if req.template_name not in valid_names:
            msg = f"System template not found: {req.template_name}"
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=msg)
        user.default_template_name = req.template_name
        user.default_template_id = None

    # --- Clear default
    else:
        user.default_template_id = None
        user.default_template_name = None

    await session.commit()
    await session.refresh(user)

    template = req.template_id or req.template_name or "Unset"
    logger.info("Updated default template %s for user %s", template, user.id)

    return GetUserResponse.from_user(user)

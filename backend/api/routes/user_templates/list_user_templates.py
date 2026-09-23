from sqlmodel import col, select

from backend.api.dependencies import UserDep
from backend.api.dependencies.get_session import SQLSessionDep
from common.database.postgres_models import UserTemplate
from common.types import TemplateResponse


async def endpoint(
    user: UserDep,
    session: SQLSessionDep,
) -> list[TemplateResponse]:
    """List all user templates for the current user, ordered by updated_datetime descending."""

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
            is_default=template.id == user.default_template_id,
        )
        for template in templates
    ]

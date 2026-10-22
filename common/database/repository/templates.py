from uuid import UUID

from sqlalchemy.orm import selectinload
from sqlmodel.ext.asyncio.session import AsyncSession

from common.database.postgres_models import UserTemplate


async def get_user_template_with_questions(session: AsyncSession, template_id: UUID) -> UserTemplate | None:
    return await session.get(UserTemplate, template_id, options=[selectinload(UserTemplate.questions)])

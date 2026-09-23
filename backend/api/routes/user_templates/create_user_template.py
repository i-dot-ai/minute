from backend.api.dependencies import UserDep
from backend.api.dependencies.get_session import SQLSessionDep
from common.database.postgres_models import TemplateQuestion, UserTemplate
from common.types import CreateUserTemplateRequest


async def endpoint(
    user: UserDep,
    session: SQLSessionDep,
    req: CreateUserTemplateRequest,
) -> None:
    """Create a new user template for the current user."""

    template = UserTemplate(
        name=req.name,
        content=req.content,
        description=req.description,
        user_id=user.id,
        type=req.type,
        questions=[
            TemplateQuestion(
                position=question.position,
                title=question.title,
                description=question.description,
            )  # type: ignore  # noqa: PGH003
            for question in (req.questions or [])
        ],
    )

    session.add(template)
    await session.commit()

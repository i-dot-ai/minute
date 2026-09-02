from typing import Annotated

from fastapi import Depends, Header, HTTPException
from sqlalchemy.dialects.postgresql import insert
from sqlmodel import func

from backend.api.dependencies.get_session import SQLSessionDep
from common.auth import get_user_info
from common.database.postgres_models import User
from common.services.exceptions import MissingAuthTokenError
from common.settings import get_settings, get_structured_logger

settings = get_settings()

logger = get_structured_logger()


async def get_or_create_user(session: SQLSessionDep, email: str) -> User:
    """Look up a user by email, creating them if this is their first request.

    Emails are normalised here so the MCP server and the API agree: different
    auth providers return different casing, and we look users up by exact
    match, so a casing change would orphan someone's data.
    """
    stmt = (
        insert(User)
        .values(email=email.lower())
        .on_conflict_do_update(
            index_elements=[func.lower(User.email)],
            set_={User.email: User.email},  # no-op, just so RETURNING fires
        )
        .returning(User)
    )
    result = await session.execute(stmt)
    await session.commit()

    return result.scalar_one()


async def get_current_user(
    session: SQLSessionDep,
    x_amzn_oidc_data: Annotated[str | None, Header()] = None,
) -> User:
    """
    Called on every endpoint to decode JWT passed in every request.
    Gets or creates the user based on the email in the JWT
    Args:
        x_amzn_oidc_data: The incoming JWT from the auth provider, passed via the frontend app
    Returns:
        User: The user matching the username in the token
    """
    authorization: str | None = x_amzn_oidc_data

    try:
        user_auth_info = get_user_info(authorization)

        if not user_auth_info.is_authorised:
            logger.info("User {email} does not have the required permissions", email=user_auth_info.email.lower())
            raise HTTPException(
                status_code=401,
                detail="User does not have the required permissions to access this resource",
                headers={"WWW-Authenticate": "Bearer"},
            )

        return await get_or_create_user(session, user_auth_info.email)
    except MissingAuthTokenError as e:
        logger.warning("No authorization header provided")
        raise HTTPException(
            status_code=401,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        ) from e
    except HTTPException:
        logger.exception("Unhandled HTTP exception")
        raise
    except Exception as e:
        logger.exception("Unhandled exception when getting user")
        raise HTTPException(
            status_code=500,
            detail="Unhandled Authorisation Error",
            headers={"WWW-Authenticate": "Bearer"},
        ) from e


UserDep = Annotated[User, Depends(get_current_user)]

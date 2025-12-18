from typing import Annotated

from fastapi import Depends, Header, HTTPException
from sqlmodel import select

from backend.api.dependencies.get_session import SQLSessionDep
from common.auth import get_user_info
from common.database.postgres_models import User
from common.services.exceptions import MissingAuthTokenError
from common.settings import get_settings, get_structured_logger

settings = get_settings()

logger = get_structured_logger()


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
        email = user_auth_info.email

        if not user_auth_info.is_authorised:
            logger.info("User {email} does not have the required permissions", email=email)
            raise HTTPException(
                status_code=401,
                detail="User does not have the required permissions to access this resource",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Try to find existing user

        statement = select(User).where(User.email == email)
        user = (await session.exec(statement)).first()

        if not user:
            # Create new user if doesn't exist
            user = User(email=email)
            session.add(user)
            await session.commit()
            await session.refresh(user)

        return user
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

import logging
from typing import Annotated

import jwt
from fastapi import Depends, Header, HTTPException
from sqlmodel import select

from backend.api.dependencies.get_session import SQLSessionDep
from common.auth import parse_auth_token
from common.database.postgres_models import User
from common.settings import get_settings

settings = get_settings()

logger = logging.getLogger(__name__)


async def get_current_user(
    session: SQLSessionDep,
    x_amzn_oidc_accesstoken: Annotated[str | None, Header()] = None,
) -> User:
    """
    Called on every endpoint to decode JWT passed in every request.
    Gets or creates the user based on the email in the JWT
    Args:
        x_amzn_oidc_accesstoken: The incoming JWT from the auth provider, passed via the frontend app
    Returns:
        User: The user matching the username in the token
    """
    authorization: str | None = x_amzn_oidc_accesstoken

    if settings.ENVIRONMENT in ["local", "integration-test"]:
        # A JWT for local testing, an example JWT from cognito, for user test@test.com
        jwt_dict = {
            "sub": "90429234-4031-7077-b9ba-60d1af121245",
            "aud": "account",
            "email_verified": "true",
            "preferred_username": "test@test.co.uk",
            "email": "test@test.co.uk",
            "username": "test@test.co.uk",
            "exp": 1727262399,
            "iss": "https://cognito-idp.eu-west-2.amazonaws.com/eu-west-2_example",
            "realm_access": {"roles": ["minute"]},
        }
        jwt_headers = {
            "typ": "JWT",
            "kid": "1234947a-59d3-467c-880c-f005c6941ffg",
            "alg": "HS256",
            "iss": "https://auth.dev.i.ai.gov.uk/realms/i_ai",
            "exp": 1727262399,
        }
        authorization = jwt.encode(jwt_dict, "secret", algorithm="HS256", headers=jwt_headers)

    if not authorization:
        logger.info("No authorization header provided")
        raise HTTPException(
            status_code=401,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        email, _ = parse_auth_token(authorization)

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

    except Exception:
        logger.exception("Failed to decode token")
        raise HTTPException(  # noqa: B904
            status_code=401,
            detail="Failed to decode token",
            headers={"WWW-Authenticate": "Bearer"},
        )


UserDep = Annotated[User, Depends(get_current_user)]

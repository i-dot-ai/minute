"""Authentication for the MCP server.

The MCP endpoint accepts the same credential as the rest of Minute, checked the
same way: the bearer token is handed to the Auth API, exactly as
`backend/api/dependencies/get_current_user.py` does with the token the load
balancer puts in `x-amzn-oidc-data`. There is no separate token store, so there
is nothing extra to revoke, expire or keep in step with the app.

Nothing issues such a token to a non-browser client yet, so today it has to come
from a signed-in browser session. An OAuth flow would obtain and refresh one
properly; it would not change this file.
"""

from contextlib import asynccontextmanager
from uuid import UUID

from fastmcp.exceptions import ToolError
from fastmcp.server.auth import AccessToken, TokenVerifier
from fastmcp.server.dependencies import get_access_token
from sqlmodel.ext.asyncio.session import AsyncSession
from starlette.concurrency import run_in_threadpool

from backend.api.dependencies.get_current_user import get_or_create_user
from common.auth import get_user_info
from common.database.postgres_database import async_engine
from common.database.postgres_models import User
from common.settings import get_structured_logger

logger = get_structured_logger()

NOT_AUTHENTICATED = "Not authenticated."

# fastmcp's AccessToken mandates a client_id.
_CLIENT_ID = "minute"


@asynccontextmanager
async def mcp_session():
    """A database session for work that runs outside FastAPI's dependency graph."""
    async with AsyncSession(async_engine, expire_on_commit=False) as session:
        yield session


class AuthApiTokenVerifier(TokenVerifier):
    """Validates a bearer token the way every other Minute request is validated.

    Returning None is what produces the 401, so an unknown token, a user the
    Auth API declines, and an Auth API that is down all look the same to the
    caller.
    """

    async def verify_token(self, token: str) -> AccessToken | None:
        try:
            # get_user_info is synchronous and does network I/O.
            # NOTE: fix in another branch.
            user_info = await run_in_threadpool(get_user_info, token)
        except Exception:
            logger.exception("Could not check an MCP token with the Auth API")
            return None

        if not user_info.is_authorised:
            logger.info(
                "MCP request from a user without access: {reason}",
                reason=user_info.auth_reason,
            )
            return None

        async with mcp_session() as session:
            user = await get_or_create_user(session, user_info.email)

        return AccessToken(token=token, client_id=_CLIENT_ID, scopes=[], subject=str(user.id))


async def get_authenticated_user(session: AsyncSession) -> User:
    """The user behind the current MCP request.

    Every tool goes through here. The `Transcription.user_id == user.id` filter
    that each tool then applies is the only thing separating one person's
    meetings from another's, so neither this nor that filter should be bypassed.
    """
    access_token = get_access_token()
    if access_token is None or access_token.subject is None:
        raise ToolError(NOT_AUTHENTICATED)

    user = await session.get(User, UUID(access_token.subject))
    if user is None:
        # The row was deleted between verification and this lookup.
        logger.warning("MCP token resolved to a user that no longer exists")
        raise ToolError(NOT_AUTHENTICATED)

    return user

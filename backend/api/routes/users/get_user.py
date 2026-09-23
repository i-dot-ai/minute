from backend.api.dependencies import UserDep
from common.types import GetUserResponse


def endpoint(
    user: UserDep,
) -> GetUserResponse:
    """Get the current user's information."""

    return GetUserResponse.from_user(user)

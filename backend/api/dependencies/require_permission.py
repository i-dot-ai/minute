"""Route-level authorization dependency.

Basic route-level check to see if a user has permission to access a resource.
"""

from collections.abc import Callable
from typing import Annotated
from uuid import UUID

from fastapi import HTTPException, Path

from backend.api.dependencies.get_current_user import UserDep
from backend.api.dependencies.get_session import SQLSessionDep
from common.authz import user_has_permission
from common.database.postgres_models import Permission, User


def require_permission(permission: Permission) -> Callable[..., User]:
    """Build a dependency requiring ``permission`` within the route's ``org_id``.

    This guards org-scoped resources only; the personal (``org_id is None``)
    context that ``context_permissions`` supports is intentionally out of scope
    here.

    On failure it raises 404 rather than 403 so we don't reveal the existence
    of resources the caller can't access.

    Returns the current user so routes can depend on it directly.
    """

    async def _dependency(
        session: SQLSessionDep,
        user: UserDep,
        org_id: Annotated[UUID, Path()],
    ) -> User:
        if not await user_has_permission(session, user.id, permission, org_id):
            raise HTTPException(status_code=404, detail="Not found")
        return user

    return _dependency

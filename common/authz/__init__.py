"""Authorization layer for Minute.

Note: SQL-backed helpers are lazy-loaded via ``__getattr__`` so
importing this package doesn't pull in the ORM models at module-load time.
"""

from .data import ROLE_PERMISSIONS, Permission, RoleName
from .models import ActorPermissions
from .policy import Action, ResourceOwnership, can

__all__ = [
    "ROLE_PERMISSIONS",
    "Action",
    "ActorPermissions",
    "Permission",
    "ResourceOwnership",
    "RoleName",
    "active_member_orgs",
    "can",
    "context_permissions",
    "query_actor_permissions",
    "user_has_permission",
]

_QUERIES_EXPORTS = {"active_member_orgs", "query_actor_permissions", "context_permissions", "user_has_permission"}


def __getattr__(name: str):
    """Lazily expose SQL-backed helpers without importing the ORM at package load."""
    if name in _QUERIES_EXPORTS:
        from common.authz import queries

        return getattr(queries, name)
    msg = f"module {__name__!r} has no attribute {name!r}"
    raise AttributeError(msg)

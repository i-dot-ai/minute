"""Authorization layer for Minute."""

from common.authz.permissions import Permission
from common.authz.roles import ROLE_PERMISSIONS, RoleName, permissions_for_role

__all__ = [
    "ROLE_PERMISSIONS",
    "Permission",
    "RoleName",
    "active_member_orgs",
    "context_permissions",
    "permissions_for_role",
    "user_has_permission",
]

_RESOLVER_EXPORTS = {"active_member_orgs", "context_permissions", "user_has_permission"}


def __getattr__(name: str):
    """Lazily expose resolver functions without importing it at package load."""
    if name in _RESOLVER_EXPORTS:
        from common.authz import resolver

        return getattr(resolver, name)
    msg = f"module {__name__!r} has no attribute {name!r}"
    raise AttributeError(msg)

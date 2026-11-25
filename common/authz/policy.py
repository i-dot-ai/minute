from dataclasses import dataclass
from enum import StrEnum
from uuid import UUID

from .data import Permission


@dataclass(frozen=True)
class ResourceOwnership:
    org_id: UUID | None
    created_by_user_id: UUID | None


@dataclass(frozen=True)
class _ActionScopes:
    own: Permission
    any_: Permission | None = None


class Action(StrEnum):
    CREATE = "create"
    READ = "read"
    EDIT = "edit"
    DELETE = "delete"
    EXPORT = "export"


_ACTION_SCOPES: dict[Action, _ActionScopes] = {
    Action.CREATE: _ActionScopes(own=Permission.FILE_CREATE),
    Action.READ: _ActionScopes(own=Permission.FILE_READ_OWN, any_=Permission.FILE_READ_ANY),
    Action.EDIT: _ActionScopes(own=Permission.FILE_EDIT_OWN),
    Action.DELETE: _ActionScopes(own=Permission.FILE_DELETE_OWN),
    Action.EXPORT: _ActionScopes(own=Permission.FILE_EXPORT_OWN),
}


def can(
    user_id: UUID,
    context_perms: frozenset[Permission],
    action: Action,
    resource: ResourceOwnership,
) -> bool:
    """Whether the user may perform ``action`` on ``resource``."""
    scopes = _ACTION_SCOPES[action]

    has_any = scopes.any_ is not None and scopes.any_ in context_perms
    has_own = scopes.own in context_perms and resource.created_by_user_id == user_id
    return has_any or has_own

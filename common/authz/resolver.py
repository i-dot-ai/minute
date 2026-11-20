"""Resolve a user's permissions from roles"""

import asyncio
import logging
from time import monotonic
from uuid import UUID

from sqlalchemy.orm import selectinload
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from common.database.postgres_models import (
    Membership,
    MembershipRole,
    Permission,
    PermissionRecord,
    Role,
    RolePermission,
)

logger = logging.getLogger(__name__)

PERSONAL_DEFAULT_ROLE = "personal_default"

_CATALOGUE_TTL_SECONDS = 1800
_catalogue_lock = asyncio.Lock()
_catalogue_cache: tuple[float, dict[str, frozenset[Permission]]] | None = None


def reset_role_permission_cache() -> None:
    """Manually reset the cached catalogue."""
    global _catalogue_cache  # noqa: PLW0603
    _catalogue_cache = None


async def _role_permission_catalogue(session: AsyncSession) -> dict[str, frozenset[Permission]]:
    """Global role/permission map, cached in-process to prevent re-querying static data."""
    global _catalogue_cache  # noqa: PLW0603
    async with _catalogue_lock:
        if _catalogue_cache is not None and monotonic() < _catalogue_cache[0]:
            return _catalogue_cache[1]

        rows = (
            await session.exec(
                select(Role.name, PermissionRecord.name)
                .join(RolePermission, RolePermission.role_id == Role.id)
                .join(PermissionRecord, PermissionRecord.id == RolePermission.permission_id)
            )
        ).all()

        grouped: dict[str, set[Permission]] = {}
        for role_name, permission_name in rows:
            try:
                grouped.setdefault(role_name, set()).add(Permission(permission_name))
            except ValueError:
                logger.warning(
                    "Ignoring unknown permission %r granted to role %r; "
                    "DB catalogue has drifted from the Permission enum",
                    permission_name,
                    role_name,
                )
                continue

        catalogue = {name: frozenset(perms) for name, perms in grouped.items()}
        _catalogue_cache = (monotonic() + _CATALOGUE_TTL_SECONDS, catalogue)
        return catalogue


async def context_permissions(session: AsyncSession, user_id: UUID, org_id: UUID | None) -> frozenset[Permission]:
    """The permissions ``user_id`` holds in a single context.

    - ``org_id is None``: ``personal_default`` role's permissions (no org check).
    - ``org_id``: the union of permissions across the roles bound to the
      user's active membership in that org. No active membership (not a member,
      or revoked) yields an empty set.
    """
    catalogue = await _role_permission_catalogue(session)

    if org_id is None:
        return catalogue.get(PERSONAL_DEFAULT_ROLE, frozenset())

    membership = (
        await session.exec(
            select(Membership)
            .where(
                Membership.user_id == user_id,
                Membership.org_id == org_id,
                Membership.is_active.is_(True),  # type: ignore[attr-defined]
            )
            .options(selectinload(Membership.membership_roles).selectinload(MembershipRole.role))
        )
    ).first()

    if membership is None:
        return frozenset()

    union: set[Permission] = set()
    for mr in membership.membership_roles:
        if mr.role is not None:
            union |= catalogue.get(mr.role.name, frozenset())
    return frozenset(union)


async def user_has_permission(
    session: AsyncSession, user_id: UUID, permission: Permission, org_id: UUID | None
) -> bool:
    """Whether ``user_id`` holds ``permission`` in the given context."""
    return permission in await context_permissions(session, user_id, org_id)

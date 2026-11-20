"""Resolve a user's permissions from roles"""

import logging
from uuid import UUID

from sqlalchemy.orm import selectinload
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from common.database.postgres_models import (
    Membership,
    MembershipRole,
    Organisation,
    Permission,
    Role,
    UserRole,
)

logger = logging.getLogger(__name__)

PERSONAL_DEFAULT_ROLE = "personal_default"


def _coerce_permissions(role_name: str, names: list[str]) -> set[Permission]:
    """Coerce a role's stored permission strings to ``Permission`` members.

    Unknown strings mean the DB role grants have drifted from the code
    catalogue; log and skip them rather than failing resolution.
    """
    perms: set[Permission] = set()
    for name in names:
        try:
            perms.add(Permission(name))
        except ValueError:
            logger.warning(
                "Ignoring unknown permission %r granted to role %r; "
                "DB role grants have drifted from the Permission catalogue",
                name,
                role_name,
            )
    return perms


async def context_permissions(session: AsyncSession, user_id: UUID, org_id: UUID | None) -> frozenset[Permission]:
    """The permissions ``user_id`` holds in a single context.

    - ``org_id is None``: the **personal/global** context. Always grants the
      ``personal_default`` baseline, unioned with any service-wide roles bound
      directly to the user via ``user_role`` (e.g. ``service_owner``).
    - ``org_id``: the union of permissions across the roles bound to the
      user's active membership in that org. No active membership (not a member,
      or revoked), or an archived org, yields an empty set.

    A role's granted permissions are read from its ``permissions`` column; the
    permission catalogue itself lives in code (``common/authz/catalogue.py``).
    """
    if org_id is None:
        roles = (
            await session.exec(
                select(Role).where(
                    (Role.name == PERSONAL_DEFAULT_ROLE)
                    | Role.id.in_(select(UserRole.role_id).where(UserRole.user_id == user_id))  # type: ignore[attr-defined]
                )
            )
        ).all()
        union: set[Permission] = set()
        for role in roles:
            union |= _coerce_permissions(role.name, role.permissions)
        return frozenset(union)

    membership = (
        await session.exec(
            select(Membership)
            .join(Organisation, Organisation.id == Membership.org_id)
            .where(
                Membership.user_id == user_id,
                Membership.org_id == org_id,
                Membership.is_active.is_(True),  # type: ignore[attr-defined]
                Organisation.is_active.is_(True),  # type: ignore[attr-defined]
            )
            .options(selectinload(Membership.membership_roles).selectinload(MembershipRole.role))
        )
    ).first()

    if membership is None:
        return frozenset()

    union = set()
    for mr in membership.membership_roles:
        if mr.role is not None:
            union |= _coerce_permissions(mr.role.name, mr.role.permissions)
    return frozenset(union)


async def user_has_permission(
    session: AsyncSession, user_id: UUID, permission: Permission, org_id: UUID | None
) -> bool:
    """Whether ``user_id`` holds ``permission`` in the given context."""
    return permission in await context_permissions(session, user_id, org_id)

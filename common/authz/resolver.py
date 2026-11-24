"""Resolve a user's permissions from roles"""

from uuid import UUID

from sqlalchemy.orm import selectinload
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from common.authz.permissions import Permission
from common.authz.roles import ROLE_PERMISSIONS, RoleName
from common.database.postgres_models import (
    Membership,
    Organisation,
    User,
)


async def context_permissions(session: AsyncSession, user_id: UUID, org_id: UUID | None) -> frozenset[Permission]:
    """The permissions ``user_id`` holds in a single context.

    - org_id is None: global context. Grants the personal_default, unioned with
      any service-wide roles held on the user (eg. service_owner).
    - org_id: org context. Union of permissions across the roles on the user's
      active membership in that org. No active membership (not a member, or left
      the org), or an archived org yields an empty set of permissions.
    """
    if org_id is None:
        global_roles = (await session.exec(select(User.roles).where(User.id == user_id))).first()
        role_names = {RoleName.PERSONAL_DEFAULT, *(global_roles or [])}
        union: set[Permission] = set()
        for role_name in role_names:
            union |= ROLE_PERMISSIONS[role_name]
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
        )
    ).first()

    if membership is None:
        return frozenset()

    union = set()
    for role_name in membership.roles:
        union |= ROLE_PERMISSIONS[role_name]
    return frozenset(union)


async def user_has_permission(
    session: AsyncSession, user_id: UUID, permission: Permission, org_id: UUID | None
) -> bool:
    """Whether ``user_id`` holds ``permission`` in the given context."""
    return permission in await context_permissions(session, user_id, org_id)


async def active_member_orgs(
    session: AsyncSession, user_id: UUID
) -> list[tuple[Organisation, list[RoleName], frozenset[Permission]]]:
    """Every active org the user is an active member of, with their authz context."""
    memberships = (
        await session.exec(
            select(Membership)
            .join(Organisation, Organisation.id == Membership.org_id)
            .where(
                Membership.user_id == user_id,
                Membership.is_active.is_(True),  # type: ignore[attr-defined]
                Organisation.is_active.is_(True),  # type: ignore[attr-defined]
            )
            .options(selectinload(Membership.organisation))
        )
    ).all()

    result: list[tuple[Organisation, list[RoleName], frozenset[Permission]]] = []
    for membership in memberships:
        roles = sorted(membership.roles)
        perms: set[Permission] = set()
        for role_name in membership.roles:
            perms |= ROLE_PERMISSIONS[role_name]
        result.append((membership.organisation, roles, frozenset(perms)))
    return result

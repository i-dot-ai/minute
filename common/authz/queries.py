from uuid import UUID

from sqlalchemy.orm import selectinload
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from common.database.postgres_models import (
    Membership,
    Organisation,
    User,
)

from .data import Permission, RoleName
from .models import ActorPermissions
from .utils import flatten_roles_to_permissions


async def query_personal_permissions(session: AsyncSession, user_id: UUID) -> frozenset[Permission]:
    """The caller's global-context permissions"""
    global_roles = (await session.exec(select(User.roles).where(User.id == user_id))).first()
    return flatten_roles_to_permissions({RoleName.PERSONAL_DEFAULT, *(global_roles or [])})


async def query_org_permissions(session: AsyncSession, user_id: UUID, org_id: UUID) -> frozenset[Permission]:
    """The caller's org-context permissions"""
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

    return flatten_roles_to_permissions(membership.roles)


# Only used for user/orgs
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
        result.append((membership.organisation, roles, flatten_roles_to_permissions(membership.roles)))
    return result


async def query_actor_permissions(session: AsyncSession, user: User) -> ActorPermissions:
    """Build the full :class:`ActorPermissions` snapshot for ``user``.

    - Personal context: personal_default unioned with any service-wide roles.
    - Each org the user is an *active* member of (in an *active* org): the union
      of permissions across the roles bound to that membership.
    """
    personal = await query_personal_permissions(session, user.id)

    memberships = (
        await session.exec(
            select(Membership)
            .join(Organisation, Organisation.id == Membership.org_id)
            .where(
                Membership.user_id == user.id,
                Membership.is_active.is_(True),  # type: ignore[attr-defined]
                Organisation.is_active.is_(True),  # type: ignore[attr-defined]
            )
        )
    ).all()

    by_org = {membership.org_id: flatten_roles_to_permissions(membership.roles) for membership in memberships}
    return ActorPermissions(user_id=user.id, personal=personal, by_org=by_org)


async def context_permissions(session: AsyncSession, user_id: UUID, org_id: UUID | None) -> frozenset[Permission]:
    """The permissions ``user_id`` holds in a single context.

    - org_id is None: global context. Grants the personal_default, unioned with
      any service-wide roles held on the user (eg. service_owner).
    - org_id: org context. Union of permissions across the roles on the user's
      active membership in that org. No active membership (not a member, or left
      the org), or an archived org yields an empty set of permissions.
    """
    if org_id is None:
        return await query_personal_permissions(session, user_id)

    return await query_org_permissions(session, user_id, org_id)


async def user_has_permission(
    session: AsyncSession, user_id: UUID, permission: Permission, org_id: UUID | None
) -> bool:
    """Whether ``user_id`` holds ``permission`` in the given context."""
    return permission in await context_permissions(session, user_id, org_id)

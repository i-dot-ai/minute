"""Organisation membership and role management."""

import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlmodel import col, select

from backend.api.dependencies import SQLSessionDep, require_permission
from common.authz import RoleName
from common.database.postgres_models import (
    Membership,
    Permission,
    User,
)
from common.types import (
    AddOrgMemberRequest,
    AddRolesRequest,
    AssignableRolesResponse,
    OrgMember,
    OrgMembersResponse,
)

members_router = APIRouter(tags=["Organisations"])

logger = logging.getLogger(__name__)

# Roles that are never assignable within an org (global/personal contexts).
_NON_ORG_ROLES = frozenset({RoleName.PERSONAL_DEFAULT, RoleName.SERVICE_OWNER})


async def _members_response(session: SQLSessionDep, org_id: UUID) -> OrgMembersResponse:
    """List an org's members with their roles (role-less members included)."""
    rows = (
        await session.exec(
            select(
                Membership.user_id,
                User.email,
                Membership.is_active,
                Membership.roles,
            )
            .join(User, User.id == Membership.user_id)
            .where(Membership.org_id == org_id)
        )
    ).all()

    members = [
        OrgMember(user_id=row.user_id, email=row.email, is_active=row.is_active, roles=list(row.roles)) for row in rows
    ]

    return OrgMembersResponse(org_id=org_id, members=members)


def _validate_roles(names: list[RoleName]) -> list[RoleName]:
    """De-duplicate requested role names, raising 404 if any are unknown.

    Names arriving via the request models are already coerced to ``RoleName`` by
    pydantic, so an unknown name would have been rejected as a 422 earlier; this
    keeps the de-dup and a defensive guard for direct callers.
    """
    unique = list(dict.fromkeys(names))
    missing = [name for name in unique if name not in set(RoleName)]
    if missing:
        raise HTTPException(status_code=404, detail=f"Unknown role(s): {sorted(missing)}")
    return unique


async def _active_admin_count(session: SQLSessionDep, org_id: UUID) -> int:
    """Number of active memberships in the org holding permissions_admin."""
    return (
        await session.exec(
            select(func.count())
            .select_from(Membership)
            .where(
                Membership.org_id == org_id,
                Membership.is_active.is_(True),  # type: ignore[attr-defined]
                col(Membership.roles).contains([RoleName.PERMISSIONS_ADMIN]),
            )
        )
    ).one()


async def _get_active_membership(session: SQLSessionDep, org_id: UUID, user_id: UUID) -> Membership:
    membership = (
        await session.exec(
            select(Membership).where(
                Membership.org_id == org_id,
                Membership.user_id == user_id,
                Membership.is_active.is_(True),  # type: ignore[attr-defined]
            )
        )
    ).first()
    if membership is None:
        raise HTTPException(status_code=404, detail="Not found")
    return membership


def _add_roles(membership: Membership, roles: list[RoleName]) -> None:
    """Grant roles to a membership, skipping any it already holds.

    Reassigns the list so SQLAlchemy detects the JSONB change.
    """
    merged = list(membership.roles)
    for role in roles:
        if role not in merged:
            merged.append(role)
    membership.roles = merged


@members_router.get(
    "/organisations/{org_id}/members",
    response_model=OrgMembersResponse,
    dependencies=[Depends(require_permission(Permission.MEMBERSHIP_MANAGE))],
)
async def list_org_members(org_id: UUID, session: SQLSessionDep) -> OrgMembersResponse:
    """List the members of an organisation."""
    return await _members_response(session, org_id)


@members_router.get(
    "/organisations/{org_id}/assignable-roles",
    response_model=AssignableRolesResponse,
    dependencies=[Depends(require_permission(Permission.MEMBERSHIP_MANAGE))],
)
async def list_assignable_roles(org_id: UUID, session: SQLSessionDep) -> AssignableRolesResponse:  # noqa: ARG001
    """Role names a permissions admin may grant to members within an org."""
    names = sorted(role for role in RoleName if role not in _NON_ORG_ROLES)
    return AssignableRolesResponse(roles=names)


@members_router.post(
    "/organisations/{org_id}/members",
    response_model=OrgMembersResponse,
    status_code=201,
    dependencies=[Depends(require_permission(Permission.MEMBERSHIP_MANAGE))],
)
async def add_org_member(org_id: UUID, data: AddOrgMemberRequest, session: SQLSessionDep) -> OrgMembersResponse:
    """Add a user to an org by email, with optional initial roles."""
    email = data.email.strip().lower()
    if not email:
        raise HTTPException(status_code=400, detail="Email cannot be blank")

    roles = _validate_roles(data.roles) if data.roles else []

    user = (await session.exec(select(User).where(func.lower(User.email) == email))).first()
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")

    membership = (
        await session.exec(select(Membership).where(Membership.org_id == org_id, Membership.user_id == user.id))
    ).first()
    if membership is None:
        membership = Membership(user_id=user.id, org_id=org_id, is_active=True)
        session.add(membership)
        await session.flush()
    else:
        membership.is_active = True

    _add_roles(membership, roles)

    await session.commit()
    logger.info("Added member to organisation {org_id}", extra={"org_id": str(org_id)})
    return await _members_response(session, org_id)


@members_router.post(
    "/organisations/{org_id}/members/{user_id}/roles",
    response_model=OrgMembersResponse,
    dependencies=[Depends(require_permission(Permission.MEMBERSHIP_MANAGE))],
)
async def add_member_roles(
    org_id: UUID, user_id: UUID, data: AddRolesRequest, session: SQLSessionDep
) -> OrgMembersResponse:
    """Grant one or more roles to an active member."""
    membership = await _get_active_membership(session, org_id, user_id)
    roles = _validate_roles(data.roles)
    _add_roles(membership, roles)

    await session.commit()
    logger.info("Granted roles in organisation {org_id}", extra={"org_id": str(org_id)})
    return await _members_response(session, org_id)


@members_router.delete(
    "/organisations/{org_id}/members/{user_id}/roles/{role_name}",
    response_model=OrgMembersResponse,
    dependencies=[Depends(require_permission(Permission.MEMBERSHIP_MANAGE))],
)
async def remove_member_role(org_id: UUID, user_id: UUID, role_name: str, session: SQLSessionDep) -> OrgMembersResponse:
    """Revoke a single role from an active member.

    Refuses (409) to remove the last active permissions_admin's admin role.
    """
    membership = await _get_active_membership(session, org_id, user_id)

    if role_name not in membership.roles:
        raise HTTPException(status_code=404, detail="Not found")

    if role_name == RoleName.PERMISSIONS_ADMIN and await _active_admin_count(session, org_id) <= 1:
        raise HTTPException(status_code=409, detail="Cannot remove the last permissions admin")

    membership.roles = [role for role in membership.roles if role != role_name]
    await session.commit()
    logger.info("Removed role in organisation {org_id}", extra={"org_id": str(org_id)})
    return await _members_response(session, org_id)


@members_router.delete(
    "/organisations/{org_id}/members/{user_id}",
    response_model=OrgMembersResponse,
    dependencies=[Depends(require_permission(Permission.MEMBERSHIP_MANAGE))],
)
async def remove_org_member(org_id: UUID, user_id: UUID, session: SQLSessionDep) -> OrgMembersResponse:
    """Remove a member from an org.

    Refuses (409) to remove the last active permissions_admin.
    """
    membership = await _get_active_membership(session, org_id, user_id)

    is_admin = RoleName.PERMISSIONS_ADMIN in membership.roles
    if is_admin and await _active_admin_count(session, org_id) <= 1:
        raise HTTPException(status_code=409, detail="Cannot remove the last permissions admin")

    membership.is_active = False
    await session.commit()
    logger.info("Removed member from organisation {org_id}", extra={"org_id": str(org_id)})
    return await _members_response(session, org_id)

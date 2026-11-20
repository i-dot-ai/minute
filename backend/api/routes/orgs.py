import logging
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.dialects.postgresql import aggregate_order_by
from sqlmodel import select

from backend.api.dependencies import SQLSessionDep, require_permission
from common.database.postgres_models import (
    Membership,
    MembershipRole,
    Permission,
    Role,
    User,
)
from common.types import OrgMember, OrgMembersResponse

orgs_router = APIRouter(tags=["Organisations"])

logger = logging.getLogger(__name__)


@orgs_router.get(
    "/orgs/{org_id}/members",
    response_model=OrgMembersResponse,
    dependencies=[Depends(require_permission(Permission.MEMBERSHIP_MANAGE))],
)
async def list_org_members(org_id: UUID, session: SQLSessionDep) -> OrgMembersResponse:
    """List the members of an organisation.

    Requires ``membership.manage`` within ``org_id``.
    """
    rows = (
        await session.exec(
            select(
                Membership.user_id,
                User.email,
                Membership.is_active,
                func.array_remove(
                    func.array_agg(aggregate_order_by(Role.name, Role.name)),
                    None,
                ).label("roles"),
            )
            .join(User, User.id == Membership.user_id)
            .outerjoin(MembershipRole, MembershipRole.membership_id == Membership.id)
            .outerjoin(Role, Role.id == MembershipRole.role_id)
            .where(Membership.org_id == org_id)
            .group_by(Membership.id, Membership.user_id, User.email, Membership.is_active)
        )
    ).all()

    members = [
        OrgMember(user_id=row.user_id, email=row.email, is_active=row.is_active, roles=list(row.roles)) for row in rows
    ]

    return OrgMembersResponse(org_id=org_id, members=members)

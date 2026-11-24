import logging
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlmodel import select

from backend.api.dependencies import SQLSessionDep, require_permission
from common.database.postgres_models import (
    Membership,
    Permission,
    User,
)
from common.types import OrgMember, OrgMembersResponse

orgs_router = APIRouter(tags=["Organisations"])

logger = logging.getLogger(__name__)


@orgs_router.get(
    "/organisations/{org_id}/members",
    response_model=OrgMembersResponse,
    dependencies=[Depends(require_permission(Permission.MEMBERSHIP_MANAGE))],
)
async def list_org_members(org_id: UUID, session: SQLSessionDep) -> OrgMembersResponse:
    """List the members of an organisation."""
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

"""Organisation CRUD: create, list, read, update, archive."""

import logging
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import select

from backend.api.dependencies import SQLSessionDep, UserDep, require_global_permission, require_permission
from common.authz.roles import RoleName
from common.database.postgres_models import (
    Membership,
    Organisation,
    Permission,
    User,
)
from common.types import (
    OrgCreateRequest,
    OrgListResponse,
    OrgSummary,
    OrgUpdateRequest,
)

crud_router = APIRouter(tags=["Organisations"])

logger = logging.getLogger(__name__)

_CREATOR_ROLES = [RoleName.MEMBER, RoleName.PERMISSIONS_ADMIN]


def _org_summary(org: Organisation) -> OrgSummary:
    """Build an OrgSummary."""
    return OrgSummary(id=org.id, name=org.name, is_active=org.is_active)


async def _get_org_or_404(session: SQLSessionDep, org_id: UUID) -> Organisation:
    org = (await session.exec(select(Organisation).where(Organisation.id == org_id))).first()
    if org is None:
        raise HTTPException(status_code=404, detail="Not found")
    return org


@crud_router.post("/organisations", response_model=OrgSummary, status_code=201)
async def create_org(
    data: OrgCreateRequest,
    session: SQLSessionDep,
    user: Annotated[User, Depends(require_global_permission(Permission.ORG_CREATE))],
) -> OrgSummary:
    """Create an organisation (service-wide action).

    The creator is made an active member and granted ``member`` +
    ``permissions_admin`` in the same transaction, so the org is never left
    without an admin.
    """
    org = Organisation(name=data.name)
    session.add(org)
    await session.flush()

    membership = Membership(user_id=user.id, org_id=org.id, is_active=True, roles=list(_CREATOR_ROLES))
    session.add(membership)

    await session.commit()
    await session.refresh(org)

    logger.info("Created organisation {org_id}", extra={"org_id": str(org.id)})
    return _org_summary(org)


@crud_router.get("/organisations", response_model=OrgListResponse)
async def list_organisations(user: UserDep, session: SQLSessionDep) -> OrgListResponse:
    """List active organisations the caller is an active member of."""
    rows = (
        await session.exec(
            select(Organisation)
            .join(Membership, Membership.org_id == Organisation.id)
            .where(
                Membership.user_id == user.id,
                Membership.is_active.is_(True),  # type: ignore[attr-defined]
                Organisation.is_active.is_(True),  # type: ignore[attr-defined]
            )
            .order_by(Organisation.name)
        )
    ).all()
    return OrgListResponse(orgs=[_org_summary(o) for o in rows])


@crud_router.get("/organisations/{org_id}", response_model=OrgSummary)
async def get_org(
    org_id: UUID,
    session: SQLSessionDep,
    _user: Annotated[User, Depends(require_permission(Permission.ORG_READ))],
) -> OrgSummary:
    """Read an organisation the caller is an active member of."""
    org = await _get_org_or_404(session, org_id)
    return _org_summary(org)


@crud_router.patch("/organisations/{org_id}", response_model=OrgSummary)
async def update_org(
    org_id: UUID,
    data: OrgUpdateRequest,
    session: SQLSessionDep,
    _user: Annotated[User, Depends(require_permission(Permission.ORG_UPDATE))],
) -> OrgSummary:
    """Update an organisation."""
    org = await _get_org_or_404(session, org_id)
    org.name = data.name
    await session.commit()
    await session.refresh(org)
    logger.info("Updated organisation {org_id}", extra={"org_id": str(org.id)})
    return _org_summary(org)


@crud_router.delete("/organisations/{org_id}", status_code=204)
async def archive_org(
    org_id: UUID,
    session: SQLSessionDep,
    _user: Annotated[User, Depends(require_permission(Permission.ORG_ARCHIVE))],
) -> None:
    """Archive an organisation."""
    org = await _get_org_or_404(session, org_id)
    org.is_active = False
    await session.commit()
    logger.info("Archived organisation {org_id}", extra={"org_id": str(org_id)})

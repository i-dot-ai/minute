"""DB-backed tests for GET /users/me/organisations.

Surfaces the orgs the calling user is an active member of, each with the
caller's roles and resolved permissions, so the UI can gate per-org controls.
Runs as the local-testing user (name.surname@domain.gov.uk).

  - active memberships are returned with correct roles + permissions;
  - an archived org is excluded;
  - an inactive (left) membership is excluded;
  - orgs the caller is not a member of are not leaked.

Requires the docker-compose Postgres (`make run`).
"""

import uuid

import pytest
import pytest_asyncio
from sqlmodel import delete
from sqlmodel.ext.asyncio.session import AsyncSession

from common.auth import get_user_info
from common.authz import RoleName
from common.database.postgres_database import async_engine
from common.database.postgres_models import (
    Membership,
    Organisation,
)
from tests.utils import get_or_create_user, get_test_client

OTHER_EMAIL = "my-orgs-other@example.com"

ROLE_MEMBER = RoleName.MEMBER
ROLE_PERMISSIONS_ADMIN = RoleName.PERMISSIONS_ADMIN

ORG_ACTIVE = "My Orgs Active"
ORG_ARCHIVED = "My Orgs Archived"
ORG_LEFT = "My Orgs Left"
ORG_NON_MEMBER = "My Orgs Non Member"
FIXTURE_ORG_NAMES = [ORG_ACTIVE, ORG_ARCHIVED, ORG_LEFT, ORG_NON_MEMBER]


def _assign(membership: Membership, *role_names: RoleName) -> None:
    membership.roles = [*membership.roles, *role_names]


@pytest_asyncio.fixture
async def my_orgs_fixture():
    """From the caller's perspective:
    - ORG_ACTIVE: active member (member + permissions_admin);
    - ORG_ARCHIVED: active membership but the org is archived (excluded);
    - ORG_LEFT: inactive membership (excluded);
    - ORG_NON_MEMBER: caller not a member, someone else is (not leaked)."""
    data: dict[str, uuid.UUID] = {}
    async with AsyncSession(async_engine, expire_on_commit=False) as session:
        caller = await get_or_create_user(session, get_user_info(None).email.lower())
        other = await get_or_create_user(session, OTHER_EMAIL)

        active = Organisation(name=ORG_ACTIVE, is_active=True)
        archived = Organisation(name=ORG_ARCHIVED, is_active=False)
        left = Organisation(name=ORG_LEFT, is_active=True)
        non_member = Organisation(name=ORG_NON_MEMBER, is_active=True)
        session.add_all([active, archived, left, non_member])
        await session.flush()

        caller_active = Membership(user_id=caller.id, org_id=active.id, is_active=True)
        caller_archived = Membership(user_id=caller.id, org_id=archived.id, is_active=True)
        caller_left = Membership(user_id=caller.id, org_id=left.id, is_active=False)
        other_non_member = Membership(user_id=other.id, org_id=non_member.id, is_active=True)
        session.add_all([caller_active, caller_archived, caller_left, other_non_member])
        await session.flush()

        _assign(caller_active, ROLE_MEMBER, ROLE_PERMISSIONS_ADMIN)
        _assign(caller_archived, ROLE_MEMBER)
        _assign(caller_left, ROLE_MEMBER)
        await session.commit()

        data = {
            "active": active.id,
            "archived": archived.id,
            "left": left.id,
            "non_member": non_member.id,
        }

    yield data

    org_ids = list(data.values())
    async with AsyncSession(async_engine) as session:
        # Role grants live on the membership rows, removed with them.
        await session.exec(delete(Membership).where(Membership.org_id.in_(org_ids)))  # type: ignore[attr-defined]
        await session.exec(delete(Organisation).where(Organisation.id.in_(org_ids)))
        await session.commit()


def _org(body: dict, org_id: uuid.UUID) -> dict | None:
    return next((o for o in body["orgs"] if o["id"] == str(org_id)), None)


@pytest.mark.asyncio(loop_scope="session")
async def test_my_organisations_returns_active_membership_with_authz(my_orgs_fixture):
    """An active membership is returned with its roles and resolved permissions."""
    async with get_test_client() as ac:
        resp = await ac.get("/users/me/organisations")
    assert resp.status_code == 200
    row = _org(resp.json(), my_orgs_fixture["active"])
    assert row is not None
    assert row["name"] == ORG_ACTIVE
    assert set(row["roles"]) == {ROLE_MEMBER, ROLE_PERMISSIONS_ADMIN}
    assert "membership.manage" in row["my_permissions"]  # from permissions_admin
    assert "file.create" in row["my_permissions"]  # from member baseline


@pytest.mark.asyncio(loop_scope="session")
async def test_my_organisations_excludes_archived_org(my_orgs_fixture):
    """An archived org is not listed even with an active membership."""
    async with get_test_client() as ac:
        resp = await ac.get("/users/me/organisations")
    assert _org(resp.json(), my_orgs_fixture["archived"]) is None


@pytest.mark.asyncio(loop_scope="session")
async def test_my_organisations_excludes_inactive_membership(my_orgs_fixture):
    """An org the caller has left (inactive membership) is not listed."""
    async with get_test_client() as ac:
        resp = await ac.get("/users/me/organisations")
    assert _org(resp.json(), my_orgs_fixture["left"]) is None


@pytest.mark.asyncio(loop_scope="session")
async def test_my_organisations_does_not_leak_non_member_orgs(my_orgs_fixture):
    """Orgs the caller is not a member of are never returned."""
    async with get_test_client() as ac:
        resp = await ac.get("/users/me/organisations")
    assert _org(resp.json(), my_orgs_fixture["non_member"]) is None

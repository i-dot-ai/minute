"""DB-backed tests for the org CRUD routes.

Covers:
  - POST /organisations: a service_owner can create (201) and is bootstrapped as
    the org's permissions_admin; a non-service_owner is forbidden (403); the
    member + role grants are transactional with org creation.
  - GET /organisations/{org_id}: an active member reads the org entity (200);
    a non-member 404s; an archived org 404s.
  - PATCH /organisations/{org_id}: a permissions_admin renames (200); a plain member
    404s.
  - DELETE /organisations/{org_id}: a permissions_admin archives (204); access then 404s
    while membership rows are preserved; a plain member 404s.

Requires the docker-compose Postgres (`make run`).
"""

import uuid

import pytest
import pytest_asyncio
from sqlmodel import delete, select
from sqlmodel.ext.asyncio.session import AsyncSession

from common.auth import get_user_info
from common.authz import RoleName
from common.database.postgres_database import async_engine
from common.database.postgres_models import (
    Membership,
    Organisation,
    Permission,
    User,
)
from tests.utils import get_or_create_user, get_test_client

PLAIN_MEMBER_EMAIL = "orgs-crud-plain-member@example.com"

ROLE_MEMBER = RoleName.MEMBER
ROLE_PERMISSIONS_ADMIN = RoleName.PERMISSIONS_ADMIN
ROLE_SERVICE_OWNER = RoleName.SERVICE_OWNER

ORG_NAME_PREFIX = "Orgs CRUD"


def _assign(membership: Membership, *role_names: RoleName) -> None:
    membership.roles = [*membership.roles, *role_names]


async def _cleanup_orgs(org_ids: list[uuid.UUID]) -> None:
    async with AsyncSession(async_engine) as session:
        # Role grants live on the membership rows, removed with them.
        await session.exec(delete(Membership).where(Membership.org_id.in_(org_ids)))  # type: ignore[attr-defined]
        await session.exec(delete(Organisation).where(Organisation.id.in_(org_ids)))
        await session.commit()


# --- POST /orgs : service-wide org creation --------------------------------


@pytest_asyncio.fixture
async def as_service_owner():
    """Grant the calling (dummy) user the service_owner role for the test."""
    async with AsyncSession(async_engine, expire_on_commit=False) as session:
        caller = await get_or_create_user(session, get_user_info(None).email.lower())
        caller.roles = [RoleName.SERVICE_OWNER]
        session.add(caller)
        await session.commit()
        caller_id = caller.id

    yield caller_id

    async with AsyncSession(async_engine) as session:
        caller = (await session.exec(select(User).where(User.id == caller_id))).first()
        if caller is not None:
            caller.roles = []
            session.add(caller)
            await session.commit()
    # Clean up any orgs the creation tests made.
    async with AsyncSession(async_engine) as session:
        org_ids = (
            await session.exec(
                select(Organisation.id).where(Organisation.name.like(f"{ORG_NAME_PREFIX}%"))  # type: ignore[attr-defined]
            )
        ).all()
    if org_ids:
        await _cleanup_orgs(list(org_ids))


@pytest.mark.asyncio(loop_scope="session")
@pytest.mark.usefixtures("as_service_owner")
async def test_create_org_allows_service_owner():
    """A service_owner creates an org and gets 201 with the org record."""
    async with get_test_client() as ac:
        resp = await ac.post("/organisations", json={"name": f"{ORG_NAME_PREFIX} Created"})
    assert resp.status_code == 201
    body = resp.json()
    assert body["name"] == f"{ORG_NAME_PREFIX} Created"
    assert body["is_active"] is True


@pytest.mark.asyncio(loop_scope="session")
@pytest.mark.usefixtures("as_service_owner")
async def test_create_org_bootstraps_creator_as_admin():
    """The creating service_owner becomes a permissions_admin of the new org.

    The create response is the org entity only (no caller context); the creator's
    resulting permissions are surfaced via GET /users/me/organisations."""
    async with get_test_client() as ac:
        resp = await ac.post("/organisations", json={"name": f"{ORG_NAME_PREFIX} Bootstrap"})
        assert resp.status_code == 201
        org_id = resp.json()["id"]

        mine = await ac.get("/users/me/organisations")
    assert mine.status_code == 200
    created = next((o for o in mine.json()["orgs"] if o["id"] == org_id), None)
    assert created is not None
    perms = set(created["my_permissions"])
    assert Permission.MEMBERSHIP_MANAGE in perms
    assert Permission.ORG_UPDATE in perms
    assert Permission.ORG_ARCHIVE in perms
    assert Permission.ORG_READ in perms  # from the member baseline


@pytest.mark.asyncio(loop_scope="session")
async def test_create_org_persists_membership_and_roles(as_service_owner):
    """Creation transactionally writes an active membership with the creator's
    member + permissions_admin roles."""
    async with get_test_client() as ac:
        resp = await ac.post("/organisations", json={"name": f"{ORG_NAME_PREFIX} Persisted"})
    org_id = uuid.UUID(resp.json()["id"])

    async with AsyncSession(async_engine, expire_on_commit=False) as session:
        membership = (
            await session.exec(
                select(Membership).where(Membership.org_id == org_id, Membership.user_id == as_service_owner)
            )
        ).first()
        assert membership is not None
        assert membership.is_active is True
        role_names = set(membership.roles)
    assert role_names == {ROLE_MEMBER, ROLE_PERMISSIONS_ADMIN}


@pytest.mark.asyncio(loop_scope="session")
async def test_create_org_forbidden_for_non_service_owner():
    """A caller without org.create is forbidden (403, not 404 - it's a
    service-wide action with no resource to conceal)."""
    async with get_test_client() as ac:
        resp = await ac.post("/organisations", json={"name": f"{ORG_NAME_PREFIX} Forbidden"})
    assert resp.status_code == 403


# --- GET / PATCH / DELETE /organisations/{org_id} : per-org CRUD ---------------------


@pytest_asyncio.fixture
async def org_fixture():
    """Two orgs from the caller's perspective:
    - org A: caller is a permissions_admin (and member);
    - org B: caller is only a plain member.
    A third user (plain_member) is a member of neither, standing in for the
    non-member case."""
    data: dict[str, uuid.UUID] = {}
    async with AsyncSession(async_engine, expire_on_commit=False) as session:
        caller = await get_or_create_user(session, get_user_info(None).email.lower())
        await get_or_create_user(session, PLAIN_MEMBER_EMAIL)

        org_a = Organisation(name=f"{ORG_NAME_PREFIX} Fixture A")
        org_b = Organisation(name=f"{ORG_NAME_PREFIX} Fixture B")
        session.add_all([org_a, org_b])
        await session.flush()

        caller_a = Membership(user_id=caller.id, org_id=org_a.id, is_active=True)
        caller_b = Membership(user_id=caller.id, org_id=org_b.id, is_active=True)
        session.add_all([caller_a, caller_b])
        await session.flush()

        _assign(caller_a, ROLE_MEMBER, ROLE_PERMISSIONS_ADMIN)
        _assign(caller_b, ROLE_MEMBER)
        await session.commit()

        data = {"caller_id": caller.id, "org_a": org_a.id, "org_b": org_b.id}

    yield data

    await _cleanup_orgs([data["org_a"], data["org_b"]])


@pytest.mark.asyncio(loop_scope="session")
async def test_get_org_allows_member(org_fixture):
    """A member reads their own org; the response is the org entity (no caller
    context / my_permissions)."""
    async with get_test_client() as ac:
        resp = await ac.get(f"/organisations/{org_fixture['org_b']}")
    assert resp.status_code == 200
    body = resp.json()
    assert body["id"] == str(org_fixture["org_b"])
    assert "my_permissions" not in body


@pytest.mark.asyncio(loop_scope="session")
async def test_get_org_404_for_non_member():
    """An org the caller is not a member of reveals nothing (404)."""
    async with AsyncSession(async_engine, expire_on_commit=False) as session:
        org = Organisation(name=f"{ORG_NAME_PREFIX} Non Member")
        session.add(org)
        await session.commit()
        org_id = org.id
    try:
        async with get_test_client() as ac:
            resp = await ac.get(f"/organisations/{org_id}")
        assert resp.status_code == 404
    finally:
        await _cleanup_orgs([org_id])


@pytest.mark.asyncio(loop_scope="session")
async def test_get_org_404_when_archived(org_fixture):
    """An archived org 404s even for a member (access stops on archive)."""
    async with AsyncSession(async_engine) as session:
        org = (await session.exec(select(Organisation).where(Organisation.id == org_fixture["org_a"]))).first()
        org.is_active = False
        await session.commit()

    async with get_test_client() as ac:
        resp = await ac.get(f"/organisations/{org_fixture['org_a']}")
    assert resp.status_code == 404


@pytest.mark.asyncio(loop_scope="session")
async def test_update_org_allows_permissions_admin(org_fixture):
    """A permissions_admin renames their org."""
    async with get_test_client() as ac:
        resp = await ac.patch(f"/organisations/{org_fixture['org_a']}", json={"name": f"{ORG_NAME_PREFIX} Renamed"})
    assert resp.status_code == 200
    assert resp.json()["name"] == f"{ORG_NAME_PREFIX} Renamed"


@pytest.mark.asyncio(loop_scope="session")
async def test_update_org_404_for_plain_member(org_fixture):
    """A plain member lacks org.update, so the update 404s."""
    async with get_test_client() as ac:
        resp = await ac.patch(f"/organisations/{org_fixture['org_b']}", json={"name": f"{ORG_NAME_PREFIX} Nope"})
    assert resp.status_code == 404


@pytest.mark.asyncio(loop_scope="session")
async def test_archive_org_allows_permissions_admin_then_blocks_access(org_fixture):
    """A permissions_admin archives the org (204); afterwards even a member
    read 404s."""
    async with get_test_client() as ac:
        archive = await ac.delete(f"/organisations/{org_fixture['org_a']}")
        assert archive.status_code == 204
        follow_up = await ac.get(f"/organisations/{org_fixture['org_a']}")
    assert follow_up.status_code == 404


@pytest.mark.asyncio(loop_scope="session")
async def test_archive_org_preserves_membership_rows(org_fixture):
    """Archiving soft-deletes the org but leaves membership rows intact."""
    async with get_test_client() as ac:
        archive = await ac.delete(f"/organisations/{org_fixture['org_a']}")
        assert archive.status_code == 204

    async with AsyncSession(async_engine, expire_on_commit=False) as session:
        memberships = (await session.exec(select(Membership).where(Membership.org_id == org_fixture["org_a"]))).all()
    assert len(memberships) >= 1


@pytest.mark.asyncio(loop_scope="session")
async def test_archive_org_404_for_plain_member(org_fixture):
    """A plain member lacks org.archive, so the archive 404s."""
    async with get_test_client() as ac:
        resp = await ac.delete(f"/organisations/{org_fixture['org_b']}")
    assert resp.status_code == 404

"""DB-backed tests for org user/role management routes.

All routes are gated on ``membership.manage``; the calling user is made a
permissions_admin of the fixture org so they can manage it.

Covers:
  - add member by email, unknown user 404s;
  - add roles to a member; unknown role 404s;
  - remove a role from a member;
  - remove a member (leaver pattern: is_active=False, rows preserved);
  - the last-admin guard (409) on removing the final permissions_admin, via
    both role-removal and member-removal;
  - non-admins get 404 (reveal-nothing).

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
    User,
)
from tests.utils import get_or_create_user, get_test_client

EXISTING_MEMBER_EMAIL = "usermgmt-existing@example.com"
NEW_MEMBER_EMAIL = "usermgmt-new@example.com"
SECOND_ADMIN_EMAIL = "usermgmt-second-admin@example.com"

ROLE_MEMBER = RoleName.MEMBER
ROLE_FILE_ADMIN = RoleName.FILE_ADMIN
ROLE_PERMISSIONS_ADMIN = RoleName.PERMISSIONS_ADMIN

ORG_NAME_PREFIX = "User Mgmt"


def _assign(membership: Membership, *role_names: RoleName) -> None:
    membership.roles = [*membership.roles, *role_names]


@pytest_asyncio.fixture
async def org_fixture():
    """One org where the caller is a permissions_admin and `existing` is a plain
    member. Extra users (new, second_admin) exist but are not members yet."""
    data: dict[str, uuid.UUID] = {}
    async with AsyncSession(async_engine, expire_on_commit=False) as session:
        caller = await get_or_create_user(session, get_user_info(None).email.lower())
        existing = await get_or_create_user(session, EXISTING_MEMBER_EMAIL)
        await get_or_create_user(session, NEW_MEMBER_EMAIL)
        second_admin = await get_or_create_user(session, SECOND_ADMIN_EMAIL)

        org = Organisation(name=f"{ORG_NAME_PREFIX} Org")
        session.add(org)
        await session.flush()

        caller_m = Membership(user_id=caller.id, org_id=org.id, is_active=True)
        existing_m = Membership(user_id=existing.id, org_id=org.id, is_active=True)
        session.add_all([caller_m, existing_m])
        await session.flush()
        _assign(caller_m, ROLE_MEMBER, ROLE_PERMISSIONS_ADMIN)
        _assign(existing_m, ROLE_MEMBER)
        await session.commit()

        data = {
            "org": org.id,
            "caller_id": caller.id,
            "existing_id": existing.id,
            "second_admin_id": second_admin.id,
        }

    yield data

    async with AsyncSession(async_engine) as session:
        # Role grants live on the membership rows, removed with them.
        await session.exec(delete(Membership).where(Membership.org_id == data["org"]))  # type: ignore[attr-defined]
        await session.exec(delete(Organisation).where(Organisation.id == data["org"]))
        await session.commit()


def _member(body: dict, email: str) -> dict | None:
    return next((m for m in body["members"] if m["email"] == email), None)


# --- add member ------------------------------------------------------------


@pytest.mark.asyncio(loop_scope="session")
async def test_assignable_roles_lists_org_roles(org_fixture):
    """The assignable-roles endpoint lists in-org roles from the DB, excluding
    the implicit personal baseline and service-wide roles."""
    async with get_test_client() as ac:
        resp = await ac.get(f"/organisations/{org_fixture['org']}/assignable-roles")
    assert resp.status_code == 200
    roles = set(resp.json()["roles"])
    assert ROLE_MEMBER in roles
    assert ROLE_FILE_ADMIN in roles
    assert ROLE_PERMISSIONS_ADMIN in roles
    assert "personal_default" not in roles
    assert "service_owner" not in roles


@pytest.mark.asyncio(loop_scope="session")
async def test_add_member_by_email(org_fixture):
    """Adding an existing user by email creates an active membership with the given role."""
    async with get_test_client() as ac:
        resp = await ac.post(
            f"/organisations/{org_fixture['org']}/members",
            json={"email": NEW_MEMBER_EMAIL, "roles": [ROLE_MEMBER]},
        )
    assert resp.status_code == 201
    row = _member(resp.json(), NEW_MEMBER_EMAIL)
    assert row is not None
    assert row["is_active"] is True
    assert row["roles"] == [ROLE_MEMBER]


@pytest.mark.asyncio(loop_scope="session")
async def test_add_member_unknown_user_404s(org_fixture):
    """Adding a user who does not exist 404s - membership never creates an account."""
    async with get_test_client() as ac:
        resp = await ac.post(
            f"/organisations/{org_fixture['org']}/members",
            json={"email": "usermgmt-nonexistent@example.com"},
        )
    assert resp.status_code == 404

    # No account was created as a side effect.
    async with AsyncSession(async_engine) as session:
        created = (await session.exec(select(User).where(User.email == "usermgmt-nonexistent@example.com"))).first()
    assert created is None


@pytest.mark.asyncio(loop_scope="session")
async def test_add_member_reactivates_prior_membership(org_fixture):
    """Re-adding a previously-removed member reactivates the membership rather
    than creating a duplicate."""
    # Deactivate the existing member first.
    async with AsyncSession(async_engine) as session:
        membership = (
            await session.exec(
                select(Membership).where(
                    Membership.org_id == org_fixture["org"],
                    Membership.user_id == org_fixture["existing_id"],
                )
            )
        ).first()
        membership.is_active = False
        await session.commit()

    async with get_test_client() as ac:
        resp = await ac.post(
            f"/organisations/{org_fixture['org']}/members",
            json={"email": EXISTING_MEMBER_EMAIL},
        )
    assert resp.status_code == 201
    row = _member(resp.json(), EXISTING_MEMBER_EMAIL)
    assert row["is_active"] is True

    async with AsyncSession(async_engine) as session:
        count = (
            await session.exec(
                select(Membership).where(
                    Membership.org_id == org_fixture["org"],
                    Membership.user_id == org_fixture["existing_id"],
                )
            )
        ).all()
    assert len(count) == 1


@pytest.mark.asyncio(loop_scope="session")
async def test_add_member_forbidden_for_non_admin():
    """A caller without membership.manage gets 404 (reveal-nothing)."""
    async with AsyncSession(async_engine, expire_on_commit=False) as session:
        org = Organisation(name=f"{ORG_NAME_PREFIX} Non Admin")
        session.add(org)
        await session.commit()
        org_id = org.id
    try:
        async with get_test_client() as ac:
            resp = await ac.post(f"/organisations/{org_id}/members", json={"email": NEW_MEMBER_EMAIL})
        assert resp.status_code == 404
    finally:
        async with AsyncSession(async_engine) as session:
            await session.exec(delete(Organisation).where(Organisation.id == org_id))
            await session.commit()


# --- roles -----------------------------------------------------------------


@pytest.mark.asyncio(loop_scope="session")
async def test_add_roles_to_member(org_fixture):
    """Granting file_admin to a plain member surfaces in their role list."""
    async with get_test_client() as ac:
        resp = await ac.post(
            f"/organisations/{org_fixture['org']}/members/{org_fixture['existing_id']}/roles",
            json={"roles": [ROLE_FILE_ADMIN]},
        )
    assert resp.status_code == 200
    row = _member(resp.json(), EXISTING_MEMBER_EMAIL)
    assert ROLE_FILE_ADMIN in row["roles"]


@pytest.mark.asyncio(loop_scope="session")
async def test_add_unknown_role_422s(org_fixture):
    """Granting a role that does not exist is rejected by request validation (422)."""
    async with get_test_client() as ac:
        resp = await ac.post(
            f"/organisations/{org_fixture['org']}/members/{org_fixture['existing_id']}/roles",
            json={"roles": ["not_a_real_role"]},
        )
    assert resp.status_code == 422


@pytest.mark.asyncio(loop_scope="session")
async def test_remove_role_from_member(org_fixture):
    """Removing a granted role drops it from the member's role list."""
    async with get_test_client() as ac:
        await ac.post(
            f"/organisations/{org_fixture['org']}/members/{org_fixture['existing_id']}/roles",
            json={"roles": [ROLE_FILE_ADMIN]},
        )
        resp = await ac.delete(
            f"/organisations/{org_fixture['org']}/members/{org_fixture['existing_id']}/roles/{ROLE_FILE_ADMIN}"
        )
    assert resp.status_code == 200
    row = _member(resp.json(), EXISTING_MEMBER_EMAIL)
    assert ROLE_FILE_ADMIN not in row["roles"]


@pytest.mark.asyncio(loop_scope="session")
async def test_remove_last_admin_role_blocked(org_fixture):
    """Removing permissions_admin from the only admin is refused (409)."""
    async with get_test_client() as ac:
        resp = await ac.delete(
            f"/organisations/{org_fixture['org']}/members/{org_fixture['caller_id']}/roles/{ROLE_PERMISSIONS_ADMIN}"
        )
    assert resp.status_code == 409


@pytest.mark.asyncio(loop_scope="session")
async def test_remove_admin_role_allowed_with_second_admin(org_fixture):
    """With two admins, removing one admin's permissions_admin role is allowed."""
    async with get_test_client() as ac:
        await ac.post(
            f"/organisations/{org_fixture['org']}/members",
            json={"email": SECOND_ADMIN_EMAIL, "roles": [ROLE_MEMBER, ROLE_PERMISSIONS_ADMIN]},
        )
        resp = await ac.delete(
            f"/organisations/{org_fixture['org']}/members/{org_fixture['caller_id']}/roles/{ROLE_PERMISSIONS_ADMIN}"
        )
    assert resp.status_code == 200


# --- remove member ---------------------------------------------------------


@pytest.mark.asyncio(loop_scope="session")
async def test_remove_member_deactivates_and_preserves_row(org_fixture):
    """Removing a member sets is_active=False and keeps the row (history)."""
    async with get_test_client() as ac:
        resp = await ac.delete(f"/organisations/{org_fixture['org']}/members/{org_fixture['existing_id']}")
    assert resp.status_code == 200
    row = _member(resp.json(), EXISTING_MEMBER_EMAIL)
    assert row["is_active"] is False

    async with AsyncSession(async_engine) as session:
        membership = (
            await session.exec(
                select(Membership).where(
                    Membership.org_id == org_fixture["org"],
                    Membership.user_id == org_fixture["existing_id"],
                )
            )
        ).first()
    assert membership is not None  # row preserved


@pytest.mark.asyncio(loop_scope="session")
async def test_remove_last_admin_member_blocked(org_fixture):
    """Removing the only permissions_admin member is refused (409)."""
    async with get_test_client() as ac:
        resp = await ac.delete(f"/organisations/{org_fixture['org']}/members/{org_fixture['caller_id']}")
    assert resp.status_code == 409


@pytest.mark.asyncio(loop_scope="session")
async def test_remove_unknown_member_404s(org_fixture):
    """Removing a user who is not an active member 404s."""
    async with get_test_client() as ac:
        resp = await ac.delete(f"/organisations/{org_fixture['org']}/members/{uuid.uuid4()}")
    assert resp.status_code == 404

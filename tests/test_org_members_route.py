"""DB-backed tests for the org-members route (``GET /orgs/{org_id}/members``).

Exercises the route across roles:
  - permissions-admin in the org -> 200 with the member list (roles surfaced,
    role-less members still listed);
  - non-member -> 404 (reveals nothing);
  - active member without membership.manage -> 404 (insufficient permission, as
    distinct from non-membership);
  - unknown org -> 404.

Requires the docker-compose Postgres (`make run`). Role/permission catalogue is
assumed seeded by migration ``c7e1a9d35f20``.
"""

import uuid

import pytest
import pytest_asyncio
from sqlmodel import delete, select
from sqlmodel.ext.asyncio.session import AsyncSession

from common.auth import get_user_info
from common.database.postgres_database import async_engine
from common.database.postgres_models import (
    Membership,
    MembershipRole,
    Organisation,
    Role,
)
from tests.utils import get_or_create_user, get_test_client

MEMBER_EMAIL = "members-route-member@example.com"
ROLELESS_EMAIL = "members-route-roleless@example.com"

ROLE_MEMBER = "member"
ROLE_PERMISSIONS_ADMIN = "permissions_admin"


async def _role_id(session: AsyncSession, name: str) -> uuid.UUID:
    role = (await session.exec(select(Role).where(Role.name == name))).first()
    assert role is not None, f"seed role {name} missing — run migrations"
    return role.id


async def _assign(session: AsyncSession, membership: Membership, *role_names: str) -> None:
    for name in role_names:
        session.add(MembershipRole(membership_id=membership.id, role_id=await _role_id(session, name)))


@pytest_asyncio.fixture
async def org_fixture():
    """Three orgs, from the calling user's perspective:
    - org A: caller is a permissions-admin; `member` is a plain member;
      `roleless` is an active member with no roles at all.
    - org B: caller is only a plain member (active membership but no
      membership.manage — proves the route 404s on insufficient permission, as
      distinct from non-membership).
    - org C: caller is not a member at all (proves the route reveals nothing
      for orgs the caller has no membership in)."""
    data: dict[str, uuid.UUID] = {}
    async with AsyncSession(async_engine, expire_on_commit=False) as session:
        caller = await get_or_create_user(session, get_user_info(None).email.lower())
        member = await get_or_create_user(session, MEMBER_EMAIL)
        roleless = await get_or_create_user(session, ROLELESS_EMAIL)

        org_a = Organisation(name="Members Route Org A")
        org_b = Organisation(name="Members Route Org B")
        org_c = Organisation(name="Members Route Org C")
        session.add_all([org_a, org_b, org_c])
        await session.flush()

        caller_a = Membership(user_id=caller.id, org_id=org_a.id, is_active=True)
        member_a = Membership(user_id=member.id, org_id=org_a.id, is_active=True)
        roleless_a = Membership(user_id=roleless.id, org_id=org_a.id, is_active=True)
        caller_b = Membership(user_id=caller.id, org_id=org_b.id, is_active=True)

        member_c = Membership(user_id=member.id, org_id=org_c.id, is_active=True)
        session.add_all([caller_a, member_a, roleless_a, caller_b, member_c])
        await session.flush()

        await _assign(session, caller_a, ROLE_MEMBER, ROLE_PERMISSIONS_ADMIN)
        await _assign(session, member_a, ROLE_MEMBER)

        await _assign(session, caller_b, ROLE_MEMBER)
        await _assign(session, member_c, ROLE_MEMBER, ROLE_PERMISSIONS_ADMIN)
        await session.commit()

        data = {
            "org_a": org_a.id,
            "org_b": org_b.id,
            "org_c": org_c.id,
        }

    yield data

    org_ids = [data["org_a"], data["org_b"], data["org_c"]]
    async with AsyncSession(async_engine) as session:
        membership_ids = (
            await session.exec(select(Membership.id).where(Membership.org_id.in_(org_ids)))  # type: ignore[attr-defined]
        ).all()
        if membership_ids:
            await session.exec(
                delete(MembershipRole).where(MembershipRole.membership_id.in_(membership_ids))  # type: ignore[attr-defined]
            )
        await session.exec(delete(Membership).where(Membership.org_id.in_(org_ids)))  # type: ignore[attr-defined]
        await session.exec(delete(Organisation).where(Organisation.id.in_(org_ids)))
        await session.commit()


@pytest.mark.asyncio(loop_scope="session")
async def test_members_route_allows_permissions_admin(org_fixture):
    """The calling user is a permissions-admin in org A and sees the member list."""
    async with get_test_client() as ac:
        resp = await ac.get(f"/orgs/{org_fixture['org_a']}/members")
    assert resp.status_code == 200
    body = resp.json()
    assert body["org_id"] == str(org_fixture["org_a"])
    emails = {m["email"] for m in body["members"]}
    assert MEMBER_EMAIL in emails
    member_row = next(m for m in body["members"] if m["email"] == MEMBER_EMAIL)
    assert member_row["roles"] == [ROLE_MEMBER]


@pytest.mark.asyncio(loop_scope="session")
async def test_members_route_includes_roleless_member(org_fixture):
    """A member with no roles is still listed (outer join), with roles == []."""
    async with get_test_client() as ac:
        resp = await ac.get(f"/orgs/{org_fixture['org_a']}/members")
    assert resp.status_code == 200
    roleless_row = next(m for m in resp.json()["members"] if m["email"] == ROLELESS_EMAIL)
    assert roleless_row["roles"] == []


@pytest.mark.asyncio(loop_scope="session")
async def test_members_route_404_for_non_member(org_fixture):
    """The caller is not a member of org C, the route reveals nothing (404)."""
    async with get_test_client() as ac:
        resp = await ac.get(f"/orgs/{org_fixture['org_c']}/members")
    assert resp.status_code == 404


@pytest.mark.asyncio(loop_scope="session")
async def test_members_route_404_for_active_member_without_manage(org_fixture):
    """The caller is an active plain member of org B but lacks membership.manage
    — still a 404, distinguishing insufficient permission from non-membership."""
    async with get_test_client() as ac:
        resp = await ac.get(f"/orgs/{org_fixture['org_b']}/members")
    assert resp.status_code == 404


@pytest.mark.asyncio(loop_scope="session")
async def test_members_route_404_for_unknown_org():
    async with get_test_client() as ac:
        resp = await ac.get(f"/orgs/{uuid.uuid4()}/members")
    assert resp.status_code == 404

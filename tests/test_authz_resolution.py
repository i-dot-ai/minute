"""DB-backed tests for permission resolution.

Covers the seeded roles and ``context_permissions``:
  - the migration seeds the expected role -> permission grants (stored as a JSON
    array on each role; the permission catalogue itself is code);
  - ``context_permissions`` unions overlapping roles within a context, scopes
    roles per org (and the personal context), and excludes inactive memberships.

Requires the docker-compose Postgres (`make run`). Roles are assumed seeded by
migration ``c7e1a9d35f20``.
"""

import uuid

import pytest
import pytest_asyncio
from sqlmodel import delete, select
from sqlmodel.ext.asyncio.session import AsyncSession

from common.auth import get_user_info
from common.authz import context_permissions
from common.authz.catalogue import Permission
from common.database.postgres_database import async_engine
from common.database.postgres_models import (
    Membership,
    MembershipRole,
    Organisation,
    Role,
    UserRole,
)
from tests.utils import get_or_create_user

MEMBER_EMAIL = "resolution-member@example.com"
OUTSIDER_EMAIL = "resolution-outsider@example.com"
SERVICE_OWNER_EMAIL = "resolution-service-owner@example.com"

ROLE_PERSONAL_DEFAULT = "personal_default"
ROLE_MEMBER = "member"
ROLE_FILE_ADMIN = "file_admin"
ROLE_PERMISSIONS_ADMIN = "permissions_admin"
ROLE_SERVICE_OWNER = "service_owner"


async def _role_id(session: AsyncSession, name: str) -> uuid.UUID:
    role = (await session.exec(select(Role).where(Role.name == name))).first()
    assert role is not None, f"seed role {name} missing — run migrations"
    return role.id


async def _assign(session: AsyncSession, membership: Membership, *role_names: str) -> None:
    for name in role_names:
        session.add(MembershipRole(membership_id=membership.id, role_id=await _role_id(session, name)))


_BASELINE = {
    Permission.FILE_CREATE,
    Permission.FILE_READ_OWN,
    Permission.FILE_EDIT_OWN,
    Permission.FILE_DELETE_OWN,
    Permission.FILE_EXPORT_OWN,
}


EXPECTED_ROLE_PERMISSIONS = {
    ROLE_PERSONAL_DEFAULT: _BASELINE,
    ROLE_MEMBER: _BASELINE | {Permission.ORG_READ},
    ROLE_FILE_ADMIN: {Permission.FILE_READ_ANY},
    ROLE_PERMISSIONS_ADMIN: {Permission.MEMBERSHIP_MANAGE, Permission.ORG_UPDATE, Permission.ORG_ARCHIVE},
}


async def _permissions_for_role(session: AsyncSession, role_name: str) -> set[Permission]:
    role = (await session.exec(select(Role).where(Role.name == role_name))).first()
    assert role is not None, f"seed role {role_name} missing — run migrations"
    return {Permission(name) for name in role.permissions}


@pytest.mark.asyncio(loop_scope="session")
async def test_seed_roles_grant_only_known_permissions():
    """Every permission granted by a seeded role is a known Permission (the DB
    role grants never drift from the code catalogue)."""
    known = {p.value for p in Permission}
    async with AsyncSession(async_engine, expire_on_commit=False) as session:
        roles = (await session.exec(select(Role))).all()
    granted = {perm for role in roles for perm in role.permissions}
    assert granted <= known


@pytest.mark.asyncio(loop_scope="session")
@pytest.mark.parametrize("role_name", list(EXPECTED_ROLE_PERMISSIONS))
async def test_seed_role_grants_expected_permissions(role_name):
    """Each seeded role grants exactly its intended permission set."""
    async with AsyncSession(async_engine, expire_on_commit=False) as session:
        granted = await _permissions_for_role(session, role_name)
    assert granted == EXPECTED_ROLE_PERMISSIONS[role_name]


# --- context_permissions --------------------------------------------------


@pytest_asyncio.fixture
async def resolution_orgs():
    """Two orgs exercising role resolution. In org A the calling user is a
    member+permissions_admin and `outsider` has an inactive membership (with
    roles, to prove an inactive membership still grants nothing). `member` is a
    plain member in A but a file_admin in org B (to prove roles are scoped per
    org)."""
    data: dict[str, uuid.UUID] = {}
    async with AsyncSession(async_engine, expire_on_commit=False) as session:
        caller = await get_or_create_user(session, get_user_info(None).email.lower())
        member = await get_or_create_user(session, MEMBER_EMAIL)
        outsider = await get_or_create_user(session, OUTSIDER_EMAIL)

        org_a = Organisation(name="Resolution Org A")
        org_b = Organisation(name="Resolution Org B")
        session.add_all([org_a, org_b])
        await session.flush()

        caller_m = Membership(user_id=caller.id, org_id=org_a.id, is_active=True)
        member_m = Membership(user_id=member.id, org_id=org_a.id, is_active=True)
        outsider_m = Membership(user_id=outsider.id, org_id=org_a.id, is_active=False)
        member_b = Membership(user_id=member.id, org_id=org_b.id, is_active=True)
        session.add_all([caller_m, member_m, outsider_m, member_b])
        await session.flush()

        await _assign(session, caller_m, ROLE_MEMBER, ROLE_PERMISSIONS_ADMIN)
        await _assign(session, member_m, ROLE_MEMBER)
        await _assign(session, outsider_m, ROLE_MEMBER, ROLE_PERMISSIONS_ADMIN)
        await _assign(session, member_b, ROLE_MEMBER, ROLE_FILE_ADMIN)
        await session.commit()

        data = {
            "caller_id": caller.id,
            "member_id": member.id,
            "outsider_id": outsider.id,
            "org_a": org_a.id,
            "org_b": org_b.id,
        }

    yield data

    async with AsyncSession(async_engine) as session:
        await session.exec(delete(MembershipRole))
        await session.exec(delete(Membership))
        await session.exec(delete(Organisation).where(Organisation.id.in_([data["org_a"], data["org_b"]])))
        await session.commit()


@pytest.mark.asyncio(loop_scope="session")
async def test_org_context_unions_overlapping_roles(resolution_orgs):
    """In an org, the permissions of a member's roles are unioned: the caller's
    member+permissions_admin membership grants both the baseline and manage."""
    async with AsyncSession(async_engine, expire_on_commit=False) as session:
        perms = await context_permissions(session, resolution_orgs["caller_id"], resolution_orgs["org_a"])

    assert Permission.FILE_CREATE in perms  # from member
    assert Permission.MEMBERSHIP_MANAGE in perms  # from permissions_admin


@pytest.mark.asyncio(loop_scope="session")
async def test_personal_context_grants_the_baseline():
    """The personal (no-org) context grants the personal_default baseline."""
    async with AsyncSession(async_engine, expire_on_commit=False) as session:
        user = await get_or_create_user(session, "personal-context@example.com")
        perms = await context_permissions(session, user.id, None)

    assert perms == _BASELINE


@pytest.mark.asyncio(loop_scope="session")
async def test_personal_context_excludes_org_only_permissions():
    """The personal context never carries org-only permissions such as manage."""
    async with AsyncSession(async_engine, expire_on_commit=False) as session:
        user = await get_or_create_user(session, "personal-context@example.com")
        perms = await context_permissions(session, user.id, None)

    assert Permission.MEMBERSHIP_MANAGE not in perms


@pytest.mark.asyncio(loop_scope="session")
async def test_context_permissions_omits_roles_from_other_orgs(resolution_orgs):
    """`member` is a plain member in org A, so file_admin's read.any (held only in
    org B) does not appear in their org A context."""
    async with AsyncSession(async_engine, expire_on_commit=False) as session:
        perms = await context_permissions(session, resolution_orgs["member_id"], resolution_orgs["org_a"])

    assert Permission.FILE_READ_ANY not in perms


@pytest.mark.asyncio(loop_scope="session")
async def test_context_permissions_includes_roles_for_the_queried_org(resolution_orgs):
    """`member` is a file_admin in org B, so read.any appears in their org B
    context."""
    async with AsyncSession(async_engine, expire_on_commit=False) as session:
        perms = await context_permissions(session, resolution_orgs["member_id"], resolution_orgs["org_b"])

    assert Permission.FILE_READ_ANY in perms


@pytest.mark.asyncio(loop_scope="session")
async def test_inactive_membership_grants_no_permissions(resolution_orgs):
    """An inactive membership grants nothing, even though its roles would
    otherwise confer permissions (a removed member loses access)."""
    async with AsyncSession(async_engine, expire_on_commit=False) as session:
        perms = await context_permissions(session, resolution_orgs["outsider_id"], resolution_orgs["org_a"])

    assert perms == frozenset()


# --- global context: service-wide user_role grants -------------------------


@pytest_asyncio.fixture
async def service_owner_user():
    """A user holding the service_owner role via a user_role grant (org-less)."""
    async with AsyncSession(async_engine, expire_on_commit=False) as session:
        user = await get_or_create_user(session, SERVICE_OWNER_EMAIL)
        role = (await session.exec(select(Role).where(Role.name == ROLE_SERVICE_OWNER))).first()
        assert role is not None, "seed role service_owner missing — run migrations"
        session.add(UserRole(user_id=user.id, role_id=role.id))
        await session.commit()
        user_id = user.id

    yield user_id

    async with AsyncSession(async_engine) as session:
        await session.exec(delete(UserRole).where(UserRole.user_id == user_id))  # type: ignore[attr-defined]
        await session.commit()


@pytest.mark.asyncio(loop_scope="session")
async def test_global_context_unions_user_role_with_baseline(service_owner_user):
    """The personal context unions the personal_default baseline with any
    service-wide roles granted via user_role (here, service_owner's org.create)."""
    async with AsyncSession(async_engine, expire_on_commit=False) as session:
        perms = await context_permissions(session, service_owner_user, None)

    assert Permission.FILE_CREATE in perms  # baseline retained
    assert Permission.ORG_CREATE in perms  # from service_owner


@pytest.mark.asyncio(loop_scope="session")
async def test_user_without_global_roles_gets_only_baseline():
    """A user with no user_role grants holds exactly the personal_default
    baseline in the global context — no org.create."""
    async with AsyncSession(async_engine, expire_on_commit=False) as session:
        user = await get_or_create_user(session, "resolution-no-global-roles@example.com")
        perms = await context_permissions(session, user.id, None)

    assert perms == _BASELINE
    assert Permission.ORG_CREATE not in perms


@pytest.mark.asyncio(loop_scope="session")
async def test_service_owner_grant_does_not_leak_into_org_context(service_owner_user):
    """A service-wide service_owner grant resolves only in the global context;
    it never confers org.create (or anything) within a specific org."""
    async with AsyncSession(async_engine, expire_on_commit=False) as session:
        org = Organisation(name="Service Owner Leak Check Org")
        session.add(org)
        await session.flush()
        membership = Membership(user_id=service_owner_user, org_id=org.id, is_active=True)
        session.add(membership)
        await session.flush()
        session.add(
            MembershipRole(
                membership_id=membership.id,
                role_id=(await session.exec(select(Role).where(Role.name == ROLE_MEMBER))).first().id,
            )
        )
        await session.commit()
        org_id = org.id

    try:
        async with AsyncSession(async_engine, expire_on_commit=False) as session:
            perms = await context_permissions(session, service_owner_user, org_id)
        assert Permission.ORG_CREATE not in perms
    finally:
        async with AsyncSession(async_engine) as session:
            membership_ids = (
                await session.exec(select(Membership.id).where(Membership.org_id == org_id))
            ).all()
            if membership_ids:
                await session.exec(
                    delete(MembershipRole).where(MembershipRole.membership_id.in_(membership_ids))  # type: ignore[attr-defined]
                )
            await session.exec(delete(Membership).where(Membership.org_id == org_id))  # type: ignore[attr-defined]
            await session.exec(delete(Organisation).where(Organisation.id == org_id))
            await session.commit()

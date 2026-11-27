"""DB-backed tests for GET /organisations (plain membership-scoped directory).

Returns id/name/is_active for active orgs the caller is an active member of.
Runs as the local-testing user.

  - active memberships are listed (id/name/is_active only, no authz fields);
  - archived orgs and inactive memberships are excluded;
  - non-member orgs are not leaked.

Requires the docker-compose Postgres (`make run`).
"""

import pytest
import pytest_asyncio
from sqlmodel import delete
from sqlmodel.ext.asyncio.session import AsyncSession

from common.auth import get_user_info
from common.database.postgres_database import async_engine
from common.database.postgres_models import Membership, Organisation
from tests.utils import get_or_create_user, get_test_client

OTHER_EMAIL = "org-directory-other@example.com"

ORG_ACTIVE = "Org Directory Active"
ORG_ARCHIVED = "Org Directory Archived"
ORG_LEFT = "Org Directory Left"
ORG_NON_MEMBER = "Org Directory Non Member"


@pytest_asyncio.fixture
async def directory_fixture():
    data = {}
    async with AsyncSession(async_engine, expire_on_commit=False) as session:
        caller = await get_or_create_user(session, get_user_info(None).email.lower())
        other = await get_or_create_user(session, OTHER_EMAIL)

        active = Organisation(name=ORG_ACTIVE, is_active=True)
        archived = Organisation(name=ORG_ARCHIVED, is_active=False)
        left = Organisation(name=ORG_LEFT, is_active=True)
        non_member = Organisation(name=ORG_NON_MEMBER, is_active=True)
        session.add_all([active, archived, left, non_member])
        await session.flush()

        session.add_all(
            [
                Membership(user_id=caller.id, org_id=active.id, is_active=True),
                Membership(user_id=caller.id, org_id=archived.id, is_active=True),
                Membership(user_id=caller.id, org_id=left.id, is_active=False),
                Membership(user_id=other.id, org_id=non_member.id, is_active=True),
            ]
        )
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
        await session.exec(delete(Membership).where(Membership.org_id.in_(org_ids)))  # type: ignore[attr-defined]
        await session.exec(delete(Organisation).where(Organisation.id.in_(org_ids)))
        await session.commit()


def _ids(body: dict) -> set[str]:
    return {o["id"] for o in body["orgs"]}


@pytest.mark.asyncio(loop_scope="session")
async def test_directory_lists_active_membership(directory_fixture):
    """An active membership in an active org is listed with id/name/is_active only."""
    async with get_test_client() as ac:
        resp = await ac.get("/organisations")
    assert resp.status_code == 200
    body = resp.json()
    row = next((o for o in body["orgs"] if o["id"] == str(directory_fixture["active"])), None)
    assert row is not None
    assert row["name"] == ORG_ACTIVE
    assert row["is_active"] is True
    assert set(row.keys()) == {"id", "name", "is_active"}  # no roles / my_permissions


@pytest.mark.asyncio(loop_scope="session")
async def test_directory_excludes_archived_left_and_non_member(directory_fixture):
    """Archived orgs, left memberships, and non-member orgs are all excluded."""
    async with get_test_client() as ac:
        resp = await ac.get("/organisations")
    ids = _ids(resp.json())
    assert str(directory_fixture["active"]) in ids
    assert str(directory_fixture["archived"]) not in ids
    assert str(directory_fixture["left"]) not in ids
    assert str(directory_fixture["non_member"]) not in ids

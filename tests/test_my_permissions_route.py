"""DB-backed tests for GET /users/me/permissions.

The endpoint surfaces the caller's service-wide permissions so the UI
can gate service-wide controls. It runs as the local-testing user
(name.surname@domain.gov.uk).

  - without any global role grant, the caller holds the baseline but not
    org.create;
  - granting service_owner (on user.roles) makes org.create appear.

Requires the docker-compose Postgres (`make run`).
"""

import pytest
import pytest_asyncio
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from common.auth import get_user_info
from common.authz.roles import RoleName
from common.database.postgres_database import async_engine
from common.database.postgres_models import Permission, User
from tests.utils import get_or_create_user, get_test_client


@pytest.mark.asyncio(loop_scope="session")
async def test_my_permissions_excludes_org_create_without_grant():
    """A plain user's global permissions include the baseline but not
    org.create."""
    # Ensure the caller has no lingering service_owner grant.
    async with AsyncSession(async_engine, expire_on_commit=False) as session:
        caller = await get_or_create_user(session, get_user_info(None).email.lower())
        caller.roles = []
        session.add(caller)
        await session.commit()

    async with get_test_client() as ac:
        resp = await ac.get("/users/me/permissions")
    assert resp.status_code == 200
    perms = set(resp.json()["permissions"])
    assert Permission.FILE_CREATE in perms
    assert Permission.ORG_CREATE not in perms


@pytest_asyncio.fixture
async def service_owner_grant():
    """Grant the calling user service_owner for the duration of the test."""
    async with AsyncSession(async_engine, expire_on_commit=False) as session:
        caller = await get_or_create_user(session, get_user_info(None).email.lower())
        caller.roles = [RoleName.SERVICE_OWNER]
        session.add(caller)
        await session.commit()
        caller_id = caller.id

    yield

    async with AsyncSession(async_engine) as session:
        caller = (await session.exec(select(User).where(User.id == caller_id))).first()
        if caller is not None:
            caller.roles = []
            session.add(caller)
            await session.commit()


@pytest.mark.asyncio(loop_scope="session")
@pytest.mark.usefixtures("service_owner_grant")
async def test_my_permissions_includes_org_create_with_service_owner():
    """A service_owner's global permissions include org.create."""
    async with get_test_client() as ac:
        resp = await ac.get("/users/me/permissions")
    assert resp.status_code == 200
    assert Permission.ORG_CREATE in set(resp.json()["permissions"])

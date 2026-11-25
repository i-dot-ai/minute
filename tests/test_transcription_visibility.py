"""DB-backed tests for org-scoped visibility of transcriptions and minutes.

Covers the own-vs-any read rule applied across the list filter and the
single-resource read/edit/delete guards, for transcriptions and for minutes /
minute versions (resolved via their parent transcription). Also the personal /
legacy case: a NULL-org transcription is visible only to its creator.

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
    JobStatus,
    Membership,
    Minute,
    MinuteVersion,
    Organisation,
    Transcription,
)
from tests.utils import get_or_create_user, get_test_client

OTHER_EMAIL = "visibility-other@example.com"
ORG_NAME_PREFIX = "Visibility"


async def _cleanup(data: dict) -> None:
    tx_ids = [v for k, v in data.items() if k.startswith("tx_")]
    org_ids = [v for k, v in data.items() if k.startswith("org_")]
    async with AsyncSession(async_engine) as session:
        minute_ids = (
            await session.exec(select(Minute.id).where(Minute.transcription_id.in_(tx_ids)))  # type: ignore[attr-defined]
        ).all()
        if minute_ids:
            await session.exec(delete(MinuteVersion).where(MinuteVersion.minute_id.in_(minute_ids)))  # type: ignore[attr-defined]
            await session.exec(delete(Minute).where(Minute.id.in_(minute_ids)))  # type: ignore[attr-defined]
        await session.exec(delete(Transcription).where(Transcription.id.in_(tx_ids)))  # type: ignore[attr-defined]
        await session.exec(delete(Membership).where(Membership.org_id.in_(org_ids)))  # type: ignore[attr-defined]
        await session.exec(delete(Organisation).where(Organisation.id.in_(org_ids)))
        await session.commit()


@pytest_asyncio.fixture
async def setup():
    """Caller + another user, both members of org A. Org B has only the other user.

    Transcriptions (each with a minute + version so the minute hops are testable):
      tx_caller_personal : caller, no org
      tx_caller_org_a    : caller, org A
      tx_other_org_a     : other, org A
      tx_other_org_b     : other, org B (caller is not a member)
      tx_other_personal  : other, no org
    """
    data: dict = {}
    async with AsyncSession(async_engine, expire_on_commit=False) as session:
        caller = await get_or_create_user(session, get_user_info(None).email.lower())
        other = await get_or_create_user(session, OTHER_EMAIL)

        org_a = Organisation(name=f"{ORG_NAME_PREFIX} Org A")
        org_b = Organisation(name=f"{ORG_NAME_PREFIX} Org B")
        session.add_all([org_a, org_b])
        await session.flush()

        caller_m = Membership(user_id=caller.id, org_id=org_a.id, is_active=True, roles=[RoleName.MEMBER])
        other_a = Membership(user_id=other.id, org_id=org_a.id, is_active=True, roles=[RoleName.MEMBER])
        other_b = Membership(user_id=other.id, org_id=org_b.id, is_active=True, roles=[RoleName.MEMBER])
        session.add_all([caller_m, other_a, other_b])
        await session.flush()

        rows = {
            "tx_caller_personal": Transcription(user_id=caller.id, org_id=None, status=JobStatus.COMPLETED),
            "tx_caller_org_a": Transcription(user_id=caller.id, org_id=org_a.id, status=JobStatus.COMPLETED),
            "tx_other_org_a": Transcription(user_id=other.id, org_id=org_a.id, status=JobStatus.COMPLETED),
            "tx_other_org_b": Transcription(user_id=other.id, org_id=org_b.id, status=JobStatus.COMPLETED),
            "tx_other_personal": Transcription(user_id=other.id, org_id=None, status=JobStatus.COMPLETED),
        }
        session.add_all(rows.values())
        await session.flush()

        minutes: dict = {}
        versions: dict = {}
        for key, tx in rows.items():
            minute = Minute(transcription_id=tx.id, template_name="General", user_id=tx.user_id, org_id=tx.org_id)
            session.add(minute)
            await session.flush()
            version = MinuteVersion(
                id=uuid.uuid4(),
                minute_id=minute.id,
                status=JobStatus.COMPLETED,
                user_id=tx.user_id,
                org_id=tx.org_id,
            )
            session.add(version)
            minutes[key] = minute
            versions[key] = version
        await session.flush()

        data = {
            "caller_id": caller.id,
            "caller_membership_a": caller_m.id,
            "org_a": org_a.id,
            "org_b": org_b.id,
            **{k: v.id for k, v in rows.items()},
            **{f"minute_{k}": v.id for k, v in minutes.items()},
            **{f"ver_{k}": v.id for k, v in versions.items()},
        }
        await session.commit()

    yield data

    await _cleanup(data)


async def _promote_caller_to_file_admin(caller_membership_id: uuid.UUID) -> None:
    async with AsyncSession(async_engine) as session:
        membership = await session.get(Membership, caller_membership_id)
        membership.roles = [*membership.roles, RoleName.FILE_ADMIN]
        session.add(membership)
        await session.commit()


async def _list_ids() -> set[str]:
    async with get_test_client() as ac:
        resp = await ac.get("/transcriptions", params={"page_size": 100})
    assert resp.status_code == 200
    return {item["id"] for item in resp.json()["items"]}


# --- list visibility -------------------------------------------------------


@pytest.mark.asyncio(loop_scope="session")
async def test_plain_member_lists_only_own(setup):
    """A plain member sees their own personal + own org-A content, nothing else."""
    ids = await _list_ids()
    assert str(setup["tx_caller_personal"]) in ids
    assert str(setup["tx_caller_org_a"]) in ids
    assert str(setup["tx_other_org_a"]) not in ids
    assert str(setup["tx_other_org_b"]) not in ids
    assert str(setup["tx_other_personal"]) not in ids


@pytest.mark.asyncio(loop_scope="session")
async def test_file_admin_lists_all_in_their_org(setup):
    """file.read.any surfaces every transcription in org A, but not org B or others' personal."""
    await _promote_caller_to_file_admin(setup["caller_membership_a"])
    ids = await _list_ids()
    assert str(setup["tx_caller_personal"]) in ids
    assert str(setup["tx_caller_org_a"]) in ids
    assert str(setup["tx_other_org_a"]) in ids  # visible via file.read.any
    assert str(setup["tx_other_org_b"]) not in ids
    assert str(setup["tx_other_personal"]) not in ids


# --- single-resource read --------------------------------------------------


@pytest.mark.asyncio(loop_scope="session")
async def test_member_cannot_read_others_org_file(setup):
    async with get_test_client() as ac:
        resp = await ac.get(f"/transcriptions/{setup['tx_other_org_a']}")
    assert resp.status_code == 404


@pytest.mark.asyncio(loop_scope="session")
async def test_member_can_read_own_org_file(setup):
    async with get_test_client() as ac:
        resp = await ac.get(f"/transcriptions/{setup['tx_caller_org_a']}")
    assert resp.status_code == 200
    assert resp.json()["org_id"] == str(setup["org_a"])


@pytest.mark.asyncio(loop_scope="session")
async def test_file_admin_can_read_but_not_edit_or_delete_others_org_file(setup):
    await _promote_caller_to_file_admin(setup["caller_membership_a"])
    async with get_test_client() as ac:
        read = await ac.get(f"/transcriptions/{setup['tx_other_org_a']}")
        edit = await ac.patch(f"/transcriptions/{setup['tx_other_org_a']}", json={"title": "hijack"})
        remove = await ac.delete(f"/transcriptions/{setup['tx_other_org_a']}")
    assert read.status_code == 200  # read.any
    assert edit.status_code == 404  # no edit.any
    assert remove.status_code == 404  # no delete.any


@pytest.mark.asyncio(loop_scope="session")
async def test_cross_org_file_is_invisible_even_to_file_admin(setup):
    await _promote_caller_to_file_admin(setup["caller_membership_a"])
    async with get_test_client() as ac:
        resp = await ac.get(f"/transcriptions/{setup['tx_other_org_b']}")
    assert resp.status_code == 404


@pytest.mark.asyncio(loop_scope="session")
async def test_personal_file_private_to_creator(setup):
    """A NULL-org transcription (personal / legacy) is visible only to its creator."""
    async with get_test_client() as ac:
        mine = await ac.get(f"/transcriptions/{setup['tx_caller_personal']}")
        theirs = await ac.get(f"/transcriptions/{setup['tx_other_personal']}")
    assert mine.status_code == 200
    assert theirs.status_code == 404


# --- minutes / versions via parent transcription ---------------------------


@pytest.mark.asyncio(loop_scope="session")
async def test_minute_read_follows_parent_transcription(setup):
    async with get_test_client() as ac:
        own = await ac.get(f"/minutes/{setup['minute_tx_caller_org_a']}")
        others = await ac.get(f"/minutes/{setup['minute_tx_other_org_a']}")
    assert own.status_code == 200
    assert others.status_code == 404


@pytest.mark.asyncio(loop_scope="session")
async def test_minute_version_read_follows_parent_transcription(setup):
    async with get_test_client() as ac:
        own = await ac.get(f"/minute_versions/{setup['ver_tx_caller_org_a']}")
        others = await ac.get(f"/minute_versions/{setup['ver_tx_other_org_a']}")
    assert own.status_code == 200
    assert others.status_code == 404


@pytest.mark.asyncio(loop_scope="session")
async def test_file_admin_reads_others_minute_but_cannot_delete(setup):
    await _promote_caller_to_file_admin(setup["caller_membership_a"])
    async with get_test_client() as ac:
        read = await ac.get(f"/minutes/{setup['minute_tx_other_org_a']}")
        delete_minute = await ac.delete(f"/minutes/{setup['minute_tx_other_org_a']}")
    assert read.status_code == 200
    assert delete_minute.status_code == 404

"""DB-backed tests for org_id stamping on recording / transcription creation.

Covers POST /recordings and the recording -> transcription propagation:
  - a member with file.create in an org stamps the recording with that org_id;
  - omitting org_id (personal space) leaves it null;
  - an org the caller is not a member of 404s (no leak), and nothing is written;
  - an org the caller belongs to but which is archived 404s;
  - POST /transcriptions copies the recording's org_id onto the transcription.

Requires docker-compose Postgres (`make run`).
"""

import uuid

import pytest
import pytest_asyncio
from sqlmodel import delete, select
from sqlmodel.ext.asyncio.session import AsyncSession

from common.auth import get_user_info
from common.authz.roles import RoleName
from common.database.postgres_database import async_engine
from common.database.postgres_models import (
    Membership,
    Minute,
    MinuteVersion,
    Organisation,
    Recording,
    Transcription,
)
from tests.utils import get_or_create_user, get_test_client

ORG_NAME_PREFIX = "Recording Org Stamp"


async def _caller_id(session: AsyncSession) -> uuid.UUID:
    return (await get_or_create_user(session, get_user_info(None).email.lower())).id


async def _cleanup_orgs(org_ids: list[uuid.UUID]) -> None:
    async with AsyncSession(async_engine) as session:
        await session.exec(delete(Membership).where(Membership.org_id.in_(org_ids)))  # type: ignore[attr-defined]
        await session.exec(delete(Organisation).where(Organisation.id.in_(org_ids)))
        await session.commit()


async def _cleanup_recordings(recording_ids: list[uuid.UUID]) -> None:
    async with AsyncSession(async_engine) as session:
        recordings = (
            await session.exec(select(Recording).where(Recording.id.in_(recording_ids)))  # type: ignore[attr-defined]
        ).all()
        transcription_ids = [r.transcription_id for r in recordings if r.transcription_id is not None]
        await session.exec(delete(Recording).where(Recording.id.in_(recording_ids)))  # type: ignore[attr-defined]
        if transcription_ids:
            minute_ids = (
                await session.exec(
                    select(Minute.id).where(Minute.transcription_id.in_(transcription_ids))  # type: ignore[attr-defined]
                )
            ).all()
            if minute_ids:
                await session.exec(delete(MinuteVersion).where(MinuteVersion.minute_id.in_(minute_ids)))  # type: ignore[attr-defined]
                await session.exec(delete(Minute).where(Minute.id.in_(minute_ids)))  # type: ignore[attr-defined]
            await session.exec(delete(Transcription).where(Transcription.id.in_(transcription_ids)))  # type: ignore[attr-defined]
        await session.commit()


@pytest_asyncio.fixture
async def orgs():
    """Two orgs from the caller's perspective:
    - member_org: caller is an active MEMBER (so holds file.create there);
    - archived_org: caller is an active MEMBER but the org is archived.
    A third org (non_member_org) has no membership for the caller.
    """
    data: dict[str, uuid.UUID] = {}
    async with AsyncSession(async_engine, expire_on_commit=False) as session:
        caller_id = await _caller_id(session)

        member_org = Organisation(name=f"{ORG_NAME_PREFIX} Member")
        archived_org = Organisation(name=f"{ORG_NAME_PREFIX} Archived", is_active=False)
        non_member_org = Organisation(name=f"{ORG_NAME_PREFIX} Non Member")
        session.add_all([member_org, archived_org, non_member_org])
        await session.flush()

        session.add_all(
            [
                Membership(user_id=caller_id, org_id=member_org.id, is_active=True, roles=[RoleName.MEMBER]),
                Membership(user_id=caller_id, org_id=archived_org.id, is_active=True, roles=[RoleName.MEMBER]),
            ]
        )
        await session.commit()

        data = {
            "caller_id": caller_id,
            "member_org": member_org.id,
            "archived_org": archived_org.id,
            "non_member_org": non_member_org.id,
        }

    yield data

    await _cleanup_orgs([data["member_org"], data["archived_org"], data["non_member_org"]])


@pytest.mark.asyncio(loop_scope="session")
async def test_create_recording_stamps_org_for_member(orgs):
    """A member with file.create stamps the recording with the chosen org_id."""
    created_ids: list[uuid.UUID] = []
    try:
        async with get_test_client() as ac:
            resp = await ac.post(
                "/recordings",
                json={"file_extension": "webm", "org_id": str(orgs["member_org"])},
            )
        assert resp.status_code == 200
        recording_id = uuid.UUID(resp.json()["id"])
        created_ids.append(recording_id)

        async with AsyncSession(async_engine, expire_on_commit=False) as session:
            recording = await session.get(Recording, recording_id)
        assert recording is not None
        assert recording.org_id == orgs["member_org"]
    finally:
        await _cleanup_recordings(created_ids)


@pytest.mark.asyncio(loop_scope="session")
@pytest.mark.usefixtures("orgs")
async def test_create_recording_personal_leaves_org_null():
    """Omitting org_id saves to the personal space (org_id stays null)."""
    created_ids: list[uuid.UUID] = []
    try:
        async with get_test_client() as ac:
            resp = await ac.post("/recordings", json={"file_extension": "webm"})
        assert resp.status_code == 200
        recording_id = uuid.UUID(resp.json()["id"])
        created_ids.append(recording_id)

        async with AsyncSession(async_engine, expire_on_commit=False) as session:
            recording = await session.get(Recording, recording_id)
        assert recording is not None
        assert recording.org_id is None
    finally:
        await _cleanup_recordings(created_ids)


@pytest.mark.asyncio(loop_scope="session")
async def test_create_recording_404_for_non_member(orgs):
    """An org the caller isn't a member of 404s and writes no recording."""
    async with get_test_client() as ac:
        resp = await ac.post(
            "/recordings",
            json={"file_extension": "webm", "org_id": str(orgs["non_member_org"])},
        )
    assert resp.status_code == 404

    async with AsyncSession(async_engine, expire_on_commit=False) as session:
        leaked = (await session.exec(select(Recording).where(Recording.org_id == orgs["non_member_org"]))).all()
    assert leaked == []


@pytest.mark.asyncio(loop_scope="session")
async def test_create_recording_404_for_archived_org(orgs):
    """A member of an archived org cannot stamp against it (404)."""
    async with get_test_client() as ac:
        resp = await ac.post(
            "/recordings",
            json={"file_extension": "webm", "org_id": str(orgs["archived_org"])},
        )
    assert resp.status_code == 404

    async with AsyncSession(async_engine, expire_on_commit=False) as session:
        leaked = (await session.exec(select(Recording).where(Recording.org_id == orgs["archived_org"]))).all()
    assert leaked == []


@pytest.mark.asyncio(loop_scope="session")
async def test_transcription_inherits_recording_org(orgs, monkeypatch):
    """POST /transcriptions copies the recording's org_id onto the transcription."""

    async def _object_exists(_key: str) -> bool:
        return True

    async def _start(*_args, **_kwargs):
        return None

    monkeypatch.setattr(
        "backend.api.routes.transcriptions.storage_service.check_object_exists",
        _object_exists,
    )
    monkeypatch.setattr(
        "backend.api.routes.transcriptions.temporal.start_transcription_workflow",
        _start,
    )

    created_ids: list[uuid.UUID] = []
    try:
        async with get_test_client() as ac:
            recording_resp = await ac.post(
                "/recordings",
                json={"file_extension": "webm", "org_id": str(orgs["member_org"])},
            )
            assert recording_resp.status_code == 200
            recording_id = uuid.UUID(recording_resp.json()["id"])
            created_ids.append(recording_id)

            transcription_resp = await ac.post(
                "/transcriptions",
                json={"recording_id": str(recording_id), "template_name": "General", "title": "Org owned"},
            )
        assert transcription_resp.status_code == 201
        transcription_id = uuid.UUID(transcription_resp.json()["id"])

        async with AsyncSession(async_engine, expire_on_commit=False) as session:
            transcription = await session.get(Transcription, transcription_id)
        assert transcription is not None
        assert transcription.org_id == orgs["member_org"]
    finally:
        await _cleanup_recordings(created_ids)

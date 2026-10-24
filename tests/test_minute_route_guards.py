"""Route-level tests for the tenant-boundary guards on the minutes routes.

Covers the API half of minute_4996 vuln-0001 (cross-user user-template IDOR in
minute creation) and vuln-0002 (cross-user AI-edit source reference), which were
previously only enforced in code without a route test.

Requires the docker-compose Postgres (`make run`).
"""

import uuid

import pytest
import pytest_asyncio
from sqlmodel import delete, select
from sqlmodel.ext.asyncio.session import AsyncSession

from common.auth import get_user_info
from common.database.postgres_database import async_engine
from common.database.postgres_models import (
    JobStatus,
    Minute,
    MinuteVersion,
    Transcription,
    UserTemplate,
)
from tests.utils import get_or_create_user, get_test_client

FOREIGN_EMAIL = "foreign-tenant@example.com"


@pytest_asyncio.fixture
async def tenants() -> dict[str, dict[str, uuid.UUID]]:
    """A recording-less transcription/minute/version/template set for the calling
    user and for a different (foreign) user."""
    ids: dict[str, dict[str, uuid.UUID]] = {"own": {}, "foreign": {}}

    async with AsyncSession(async_engine, expire_on_commit=False) as session:
        own = await get_or_create_user(session, get_user_info(None).email.lower())
        foreign = await get_or_create_user(session, FOREIGN_EMAIL)

        for key, user in (("own", own), ("foreign", foreign)):
            transcription = Transcription(user_id=user.id, status=JobStatus.COMPLETED)
            template = UserTemplate(user_id=user.id, name=f"{key} template", content="<p>x</p>")
            session.add(transcription)
            session.add(template)
            await session.flush()
            minute = Minute(template_name="General", transcription_id=transcription.id)
            minute_version = MinuteVersion(minute_id=minute.id, status=JobStatus.COMPLETED)
            session.add(minute)
            session.add(minute_version)
            await session.flush()
            ids[key] = {
                "user_id": user.id,
                "transcription_id": transcription.id,
                "template_id": template.id,
                "minute_id": minute.id,
                "minute_version_id": minute_version.id,
            }
        await session.commit()

    yield ids

    async with AsyncSession(async_engine) as session:
        for key in ("own", "foreign"):
            t = ids[key]
            await session.exec(delete(MinuteVersion).where(MinuteVersion.id == t["minute_version_id"]))
            await session.exec(delete(Minute).where(Minute.id == t["minute_id"]))
            await session.exec(delete(Transcription).where(Transcription.id == t["transcription_id"]))
            await session.exec(delete(UserTemplate).where(UserTemplate.id == t["template_id"]))
        await session.commit()


@pytest.fixture(autouse=True)
def started(monkeypatch):
    started: list = []

    async def _start_generation(minute_version_id):
        started.append(("generate", str(minute_version_id)))

    async def _start_edit(minute_version_id, source_minute_version_id):
        started.append(("edit", str(minute_version_id), str(source_minute_version_id)))

    monkeypatch.setattr("backend.api.routes.minutes.temporal.start_minute_generation_workflow", _start_generation)
    monkeypatch.setattr("backend.api.routes.minutes.temporal.start_minute_edit_workflow", _start_edit)
    return started


@pytest.mark.asyncio(loop_scope="session")
async def test_create_minute_rejects_foreign_template(tenants, started):
    foreign = tenants["foreign"]
    async with get_test_client() as ac:
        response = await ac.post(
            f"/transcription/{tenants['own']['transcription_id']}/minutes",
            json={"template_name": "General", "template_id": str(foreign["template_id"])},
        )
    assert response.status_code == 404
    assert started == []


@pytest.mark.asyncio(loop_scope="session")
async def test_create_minute_accepts_own_template(tenants, started):
    own = tenants["own"]
    async with get_test_client() as ac:
        response = await ac.post(
            f"/transcription/{own['transcription_id']}/minutes",
            json={"template_name": "General", "template_id": str(own["template_id"])},
        )
    assert response.status_code == 200
    assert len(started) == 1
    assert started[0][0] == "generate"


@pytest.mark.asyncio(loop_scope="session")
async def test_create_minute_version_rejects_foreign_source(tenants, started):
    own, foreign = tenants["own"], tenants["foreign"]
    async with get_test_client() as ac:
        response = await ac.post(
            f"/minutes/{own['minute_id']}/versions",
            json={
                "content_source": "ai_edit",
                "ai_edit_instructions": {
                    "instruction": "Summarise this",
                    "source_id": str(foreign["minute_version_id"]),
                },
            },
        )
    assert response.status_code == 404
    assert started == []


@pytest.mark.asyncio(loop_scope="session")
async def test_create_minute_version_accepts_own_source(tenants, started):
    own = tenants["own"]
    async with get_test_client() as ac:
        response = await ac.post(
            f"/minutes/{own['minute_id']}/versions",
            json={
                "content_source": "ai_edit",
                "ai_edit_instructions": {"instruction": "Summarise this", "source_id": str(own["minute_version_id"])},
            },
        )
    assert response.status_code == 200
    assert len(started) == 1
    assert started[0] == ("edit", response.json()["id"], str(own["minute_version_id"]))


async def _start_boom(*_args):
    msg = "temporal unavailable"
    raise RuntimeError(msg)


@pytest.mark.asyncio(loop_scope="session")
async def test_create_minute_start_failure_marks_failed(tenants, monkeypatch):
    """A definite enqueue failure marks the committed version failed."""
    own = tenants["own"]
    monkeypatch.setattr("backend.api.routes.minutes.temporal.start_minute_generation_workflow", _start_boom)

    async with get_test_client() as ac:
        response = await ac.post(
            f"/transcription/{own['transcription_id']}/minutes",
            json={"template_name": "General", "template_id": str(own["template_id"])},
        )

    assert response.status_code == 503
    async with AsyncSession(async_engine) as session:
        versions = (
            await session.exec(
                select(MinuteVersion).join(Minute).where(Minute.transcription_id == own["transcription_id"])
            )
        ).all()
    assert any(version.status == JobStatus.FAILED for version in versions)


@pytest.mark.asyncio(loop_scope="session")
async def test_create_minute_version_start_failure_marks_failed(tenants, monkeypatch):
    """The AI-edit route applies the same enqueue compensation."""
    own = tenants["own"]
    monkeypatch.setattr("backend.api.routes.minutes.temporal.start_minute_edit_workflow", _start_boom)

    async with get_test_client() as ac:
        response = await ac.post(
            f"/minutes/{own['minute_id']}/versions",
            json={
                "content_source": "ai_edit",
                "ai_edit_instructions": {"instruction": "Summarise", "source_id": str(own["minute_version_id"])},
            },
        )

    assert response.status_code == 503
    async with AsyncSession(async_engine) as session:
        versions = (await session.exec(select(MinuteVersion).where(MinuteVersion.minute_id == own["minute_id"]))).all()
    assert any(version.status == JobStatus.FAILED for version in versions)

"""Tests for the recording-reuse guard on POST /transcriptions (vuln-0001).

Rows are seeded straight into Postgres; the S3 existence check and the workflow
start are patched. Requires the docker-compose Postgres (`make run`).
"""

import asyncio
import uuid
from contextlib import suppress

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
    Recording,
    Transcription,
)
from tests.utils import get_or_create_user, get_test_client


async def _current_user_id(session: AsyncSession) -> uuid.UUID:
    return (await get_or_create_user(session, get_user_info(None).email.lower())).id


@pytest_asyncio.fixture
async def recordings() -> dict[str, Recording]:
    recordings_by_name: dict[str, Recording] = {}

    async with AsyncSession(async_engine, expire_on_commit=False) as session:
        user_id = await _current_user_id(session)
        linked_transcription = Transcription(user_id=user_id)
        session.add(linked_transcription)
        await session.flush()
        linked = Recording(
            user_id=user_id, s3_file_key=f"reusetest/{uuid.uuid4().hex}.mp3", transcription_id=linked_transcription.id
        )
        fresh = Recording(user_id=user_id, s3_file_key=f"reusetest/{uuid.uuid4().hex}.mp3")
        session.add(linked)
        session.add(fresh)
        await session.commit()
        recordings_by_name.update(linked=linked, fresh=fresh)

    yield recordings_by_name

    linked, fresh = recordings_by_name["linked"], recordings_by_name["fresh"]
    async with AsyncSession(async_engine) as session:
        for recording in (linked, fresh):
            minute = (
                await session.exec(select(Minute).where(Minute.transcription_id == recording.transcription_id))
            ).first()
            if minute:
                await session.exec(delete(MinuteVersion).where(MinuteVersion.minute_id == minute.id))
                await session.exec(delete(Minute).where(Minute.id == minute.id))
            await session.exec(delete(Transcription).where(Transcription.id == recording.transcription_id))
        await session.commit()


@pytest.fixture(autouse=True)
def _patch_storage(monkeypatch):
    async def _object_exists(_key: str) -> bool:
        return True

    monkeypatch.setattr(
        "backend.api.routes.transcriptions.storage_service.check_object_exists",
        _object_exists,
    )


@pytest.mark.asyncio(loop_scope="session")
async def test_reused_recording_rejected(recordings):
    """vuln-0001: submitting a recording that is already linked to a transcription
    must not re-link it, orphan the original transcription, or queue more work."""
    linked = recordings["linked"]

    async with get_test_client() as ac:
        response = await ac.post(
            "/transcriptions",
            json={"recording_id": str(linked.id), "template_name": "General", "title": "Second attempt"},
        )

    assert response.status_code == 409
    # the recording's linkage is unchanged (still points at the first transcription)
    async with AsyncSession(async_engine) as session:
        recording = await session.get(Recording, linked.id)
        assert str(recording.transcription_id) == str(linked.transcription_id)


@pytest.mark.asyncio(loop_scope="session")
async def test_fresh_recording_still_creates_transcription(recordings, monkeypatch):
    started: list = []

    async def _start(transcription_id, minute_id):
        started.append((transcription_id, minute_id))

    monkeypatch.setattr(
        "backend.api.routes.transcriptions.temporal.start_transcription_workflow",
        _start,
    )
    fresh = recordings["fresh"]

    async with get_test_client() as ac:
        response = await ac.post(
            "/transcriptions",
            json={"recording_id": str(fresh.id), "template_name": "General", "title": "New job"},
        )

    assert response.status_code == 201
    assert len(started) == 1
    async with AsyncSession(async_engine) as session:
        recording = await session.get(Recording, fresh.id)
        assert recording.transcription_id is not None
        transcription = await session.get(Transcription, recording.transcription_id)
        assert transcription is not None


@pytest.mark.asyncio(loop_scope="session")
async def test_concurrent_reuse_creates_and_queues_only_one_transcription(recordings, monkeypatch):
    """Both requests read the unlinked row before either continues; only one may claim it."""
    fresh = recordings["fresh"]
    both_checked_storage = asyncio.Event()
    checks = 0
    started: list = []

    async def _object_exists(_key: str) -> bool:
        nonlocal checks
        checks += 1
        if checks == 2:
            both_checked_storage.set()
        with suppress(TimeoutError):
            await asyncio.wait_for(both_checked_storage.wait(), timeout=0.1)
        return True

    async def _start(transcription_id, minute_id):
        started.append((transcription_id, minute_id))

    monkeypatch.setattr(
        "backend.api.routes.transcriptions.storage_service.check_object_exists",
        _object_exists,
    )
    monkeypatch.setattr(
        "backend.api.routes.transcriptions.temporal.start_transcription_workflow",
        _start,
    )

    async with get_test_client() as first, get_test_client() as second:
        responses = await asyncio.gather(
            first.post(
                "/transcriptions",
                json={"recording_id": str(fresh.id), "template_name": "General", "title": "Concurrent first"},
            ),
            second.post(
                "/transcriptions",
                json={"recording_id": str(fresh.id), "template_name": "General", "title": "Concurrent second"},
            ),
        )

    # Remove the transcription which lost the last-write-wins linkage so this
    # intentionally failing test remains repeatable. The fixture removes the winner.
    async with AsyncSession(async_engine) as session:
        recording = await session.get(Recording, fresh.id)
        response_ids = {uuid.UUID(response.json()["id"]) for response in responses if response.status_code == 201}
        for transcription_id in response_ids - {recording.transcription_id}:
            minute = (await session.exec(select(Minute).where(Minute.transcription_id == transcription_id))).first()
            if minute:
                await session.exec(delete(MinuteVersion).where(MinuteVersion.minute_id == minute.id))
                await session.exec(delete(Minute).where(Minute.id == minute.id))
            await session.exec(delete(Transcription).where(Transcription.id == transcription_id))
        await session.commit()

    assert sorted(response.status_code for response in responses) == [201, 409]
    assert len(started) == 1


@pytest.mark.asyncio(loop_scope="session")
async def test_publish_failure_marks_transcription_failed(recordings, monkeypatch):
    """A definite enqueue failure leaves the committed job explicitly retryable."""
    fresh = recordings["fresh"]

    async def _boom(_transcription_id, _minute_id):
        msg = "temporal unavailable"
        raise RuntimeError(msg)

    monkeypatch.setattr(
        "backend.api.routes.transcriptions.temporal.start_transcription_workflow",
        _boom,
    )

    async with get_test_client() as ac:
        response = await ac.post(
            "/transcriptions",
            json={"recording_id": str(fresh.id), "template_name": "General", "title": "X"},
        )

    assert response.status_code == 503
    async with AsyncSession(async_engine) as session:
        recording = await session.get(Recording, fresh.id)
        assert recording.transcription_id is not None
        transcription = await session.get(Transcription, recording.transcription_id)
        assert transcription.status == JobStatus.FAILED

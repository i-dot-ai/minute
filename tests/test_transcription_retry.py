"""Tests for the POST /transcriptions/{id}/retry endpoint.

Rows are seeded straight into Postgres. The S3 existence check and the queue
publish are patched so the test neither touches object storage nor enqueues
real transcription work.

Requires the docker-compose Postgres (`make run`).
"""

import uuid
from datetime import UTC, datetime, timedelta

import pytest
import pytest_asyncio
from sqlmodel import col, delete, select
from sqlmodel.ext.asyncio.session import AsyncSession

from backend.auth import get_user_info
from common.database.postgres_database import async_engine
from common.database.postgres_models import (
    JobStatus,
    Minute,
    MinuteVersion,
    Recording,
    Transcription,
    User,
)
from common.types import TaskType
from tests.utils import get_test_client

SEED_TIME = datetime.now(UTC) - timedelta(minutes=10)


async def _current_user_id(session: AsyncSession) -> uuid.UUID:
    email = get_user_info(None).email.lower()
    user = (await session.exec(select(User).where(User.email == email))).first()
    if user is None:
        user = User(email=email)
        session.add(user)
        await session.commit()
        await session.refresh(user)
    return user.id


async def _seed_failed_transcription(
    status: JobStatus = JobStatus.FAILED, extra_versions: int = 0
) -> dict[str, uuid.UUID]:
    async with AsyncSession(async_engine, expire_on_commit=False) as session:
        user_id = await _current_user_id(session)
        transcription = Transcription(
            user_id=user_id,
            status=status,
            error="boom",
            created_datetime=SEED_TIME,
            dialogue_entries=[{"speaker": "A", "text": "body", "start_time": 0.0, "end_time": 1.0}],
        )
        session.add(transcription)
        recording = Recording(
            user_id=user_id,
            s3_file_key=f"retrytest/{uuid.uuid4().hex}.mp3",
            transcription_id=transcription.id,
        )
        minute = Minute(
            template_name="Old template",
            agenda="Old agenda",
            transcription_id=transcription.id,
        )
        minute_version = MinuteVersion(
            minute_id=minute.id,
            status=JobStatus.FAILED,
            error="boom",
            html_content="stale content",
        )
        session.add(recording)
        session.add(minute)
        session.add(minute_version)
        for _ in range(extra_versions):
            session.add(MinuteVersion(minute_id=minute.id, status=JobStatus.COMPLETED))
        await session.commit()
        return {
            "transcription_id": transcription.id,
            "minute_id": minute.id,
            "minute_version_id": minute_version.id,
        }


async def _delete_transcription(transcription_id: uuid.UUID) -> None:
    async with AsyncSession(async_engine) as session:
        await session.exec(delete(Recording).where(col(Recording.transcription_id) == transcription_id))
        await session.exec(delete(Transcription).where(col(Transcription.id) == transcription_id))
        await session.commit()


@pytest_asyncio.fixture
async def failed_transcription():
    ids = await _seed_failed_transcription()
    yield ids
    await _delete_transcription(ids["transcription_id"])


@pytest_asyncio.fixture
async def in_progress_transcription():
    ids = await _seed_failed_transcription(status=JobStatus.IN_PROGRESS)
    yield ids
    await _delete_transcription(ids["transcription_id"])


@pytest.fixture(autouse=True)
def published_messages(monkeypatch):
    published: list = []

    async def _object_exists(_key: str) -> bool:
        return True

    monkeypatch.setattr(
        "backend.api.routes.transcriptions.storage_service.check_object_exists",
        _object_exists,
    )
    monkeypatch.setattr(
        "backend.api.routes.transcriptions.transcription_queue_service.publish_message",
        published.append,
    )
    return published


@pytest.mark.asyncio(loop_scope="session")
async def test_retry_resets_existing_transcription(failed_transcription, published_messages):
    transcription_id = failed_transcription["transcription_id"]
    minute_id = failed_transcription["minute_id"]

    async with get_test_client() as ac:
        response = await ac.post(
            f"/transcriptions/{transcription_id}/retry",
            json={"template_name": "New template", "agenda": "New agenda"},
        )

    assert response.status_code == 201
    assert response.json()["id"] == str(transcription_id)

    async with AsyncSession(async_engine) as session:
        transcription = await session.get(Transcription, transcription_id)
        assert transcription.status == JobStatus.AWAITING_START
        assert transcription.error is None
        assert transcription.dialogue_entries is None
        assert transcription.created_datetime > SEED_TIME

        minute = await session.get(Minute, minute_id)
        assert minute.template_name == "New template"
        assert minute.agenda == "New agenda"

        version = await session.get(MinuteVersion, failed_transcription["minute_version_id"])
        assert version.status == JobStatus.AWAITING_START
        assert version.error is None
        assert version.html_content == ""

    published = published_messages
    assert len(published) == 1
    assert published[0].id == failed_transcription["minute_version_id"]
    assert published[0].type == TaskType.MINUTE


@pytest.mark.asyncio(loop_scope="session")
async def test_retry_rejects_non_failed_transcription(in_progress_transcription):
    transcription_id = in_progress_transcription["transcription_id"]
    async with get_test_client() as ac:
        response = await ac.post(
            f"/transcriptions/{transcription_id}/retry",
            json={"template_name": "General"},
        )
    assert response.status_code == 400


@pytest.mark.asyncio(loop_scope="session")
async def test_retry_returns_404_for_unknown_transcription():
    async with get_test_client() as ac:
        response = await ac.post(
            f"/transcriptions/{uuid.uuid4()}/retry",
            json={"template_name": "General"},
        )
    assert response.status_code == 404


@pytest.mark.asyncio(loop_scope="session")
async def test_retry_rejects_minute_with_multiple_versions(published_messages):
    ids = await _seed_failed_transcription(extra_versions=1)
    try:
        async with get_test_client() as ac:
            response = await ac.post(
                f"/transcriptions/{ids['transcription_id']}/retry",
                json={"template_name": "General"},
            )
        assert response.status_code == 400
        assert published_messages == []
    finally:
        await _delete_transcription(ids["transcription_id"])

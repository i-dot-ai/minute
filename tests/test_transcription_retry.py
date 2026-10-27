"""Tests for the POST /transcriptions/{id}/retry endpoint.

Rows are seeded straight into Postgres. The S3 existence check and the workflow
start are patched so the test neither touches object storage nor enqueues
real transcription work.

Requires the docker-compose Postgres (`make run`).
"""

import asyncio
import uuid
from datetime import UTC, datetime, timedelta

import pytest
import pytest_asyncio
from sqlmodel import col, delete
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

SEED_TIME = datetime.now(UTC) - timedelta(minutes=10)


async def _current_user_id(session: AsyncSession) -> uuid.UUID:
    return (await get_or_create_user(session, get_user_info(None).email.lower())).id


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
def started_workflows(monkeypatch):
    started: list = []

    async def _object_exists(_key: str) -> bool:
        return True

    async def _start(transcription_id, minute_id):
        started.append((transcription_id, minute_id))

    async def _running(_transcription_id):
        return False

    monkeypatch.setattr(
        "backend.api.routes.transcriptions.storage_service.check_object_exists",
        _object_exists,
    )
    monkeypatch.setattr(
        "backend.api.routes.transcriptions.temporal.start_transcription_workflow",
        _start,
    )
    monkeypatch.setattr("backend.api.routes.transcriptions.temporal.transcription_workflow_running", _running)
    return started


@pytest.mark.asyncio(loop_scope="session")
@pytest.mark.parametrize("running", [True, None])
async def test_retry_does_not_reset_data_until_previous_workflow_is_closed(
    failed_transcription, started_workflows, monkeypatch, running
):
    async def _running(_transcription_id):
        if running is None:
            msg = "Temporal unavailable"
            raise ConnectionError(msg)
        return running

    monkeypatch.setattr("backend.api.routes.transcriptions.temporal.transcription_workflow_running", _running)
    transcription_id = failed_transcription["transcription_id"]
    async with get_test_client() as ac:
        response = await ac.post(f"/transcriptions/{transcription_id}/retry", json={"template_name": "New template"})
    assert response.status_code == (409 if running else 503)
    assert started_workflows == []
    async with AsyncSession(async_engine) as session:
        transcription = await session.get(Transcription, transcription_id)
        assert transcription.status == JobStatus.FAILED
        assert transcription.error == "boom"
        assert transcription.dialogue_entries[0]["text"] == "body"
        assert transcription.created_datetime == SEED_TIME
        minute = await session.get(Minute, failed_transcription["minute_id"])
        assert minute.template_name == "Old template"
        version = await session.get(MinuteVersion, failed_transcription["minute_version_id"])
        assert version.status == JobStatus.FAILED
        assert version.html_content == "stale content"


@pytest.mark.asyncio(loop_scope="session")
@pytest.mark.parametrize("fails_immediately", [False, True])
async def test_retry_concurrent_requests_publish_once(
    failed_transcription, started_workflows, monkeypatch, fails_immediately
):
    """A stale request cannot reset a newer attempt, even when it has already failed again."""
    transcription_id = failed_transcription["transcription_id"]
    minute_id = failed_transcription["minute_id"]
    both_checked, first_started = asyncio.Event(), asyncio.Event()
    checks = 0

    async def _object_exists(_key):
        nonlocal checks
        checks += 1
        if checks == 1:
            await both_checked.wait()
        else:
            both_checked.set()
            await first_started.wait()
        return True

    async def _start(tid, mid):
        started_workflows.append((tid, mid))
        if fails_immediately:
            async with AsyncSession(async_engine) as session:
                transcription = await session.get(Transcription, tid)
                transcription.status = JobStatus.FAILED
                transcription.error = "New attempt failed"
                version = await session.get(MinuteVersion, failed_transcription["minute_version_id"])
                version.status = JobStatus.FAILED
                version.error = "New attempt failed"
                version.html_content = "New attempt content"
                await session.commit()
        first_started.set()

    monkeypatch.setattr("backend.api.routes.transcriptions.storage_service.check_object_exists", _object_exists)
    monkeypatch.setattr("backend.api.routes.transcriptions.temporal.start_transcription_workflow", _start)

    async with get_test_client() as ac:
        responses = await asyncio.wait_for(
            asyncio.gather(
                ac.post(f"/transcriptions/{transcription_id}/retry", json={"template_name": "General"}),
                ac.post(f"/transcriptions/{transcription_id}/retry", json={"template_name": "Stale template"}),
            ),
            timeout=10,
        )

    status_codes = sorted(response.status_code for response in responses)
    assert status_codes == [201, 400]
    assert len(started_workflows) == 1
    assert started_workflows[0] == (transcription_id, minute_id)

    async with AsyncSession(async_engine) as session:
        transcription = await session.get(Transcription, transcription_id)
        assert transcription.status == (JobStatus.FAILED if fails_immediately else JobStatus.AWAITING_START)
        assert transcription.error == ("New attempt failed" if fails_immediately else None)
        minute = await session.get(Minute, minute_id)
        assert minute.template_name == "General"
        version = await session.get(MinuteVersion, failed_transcription["minute_version_id"])
        assert version.status == (JobStatus.FAILED if fails_immediately else JobStatus.AWAITING_START)
        assert version.error == ("New attempt failed" if fails_immediately else None)
        assert version.html_content == ("New attempt content" if fails_immediately else "")


@pytest.mark.asyncio(loop_scope="session")
async def test_retry_resets_existing_transcription(failed_transcription, started_workflows):
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

    published = started_workflows
    assert len(published) == 1
    assert published[0] == (transcription_id, minute_id)


@pytest.mark.asyncio(loop_scope="session")
async def test_retry_rejections(in_progress_transcription, started_workflows):
    async with get_test_client() as ac:
        # Unknown transcription.
        unknown = await ac.post(f"/transcriptions/{uuid.uuid4()}/retry", json={"template_name": "General"})
        assert unknown.status_code == 404

        # Not in a failed (terminal) state.
        not_failed = await ac.post(
            f"/transcriptions/{in_progress_transcription['transcription_id']}/retry",
            json={"template_name": "General"},
        )
        assert not_failed.status_code == 400

    # A minute with more than one version cannot be retried.
    ids = await _seed_failed_transcription(extra_versions=1)
    try:
        async with get_test_client() as ac:
            multi = await ac.post(
                f"/transcriptions/{ids['transcription_id']}/retry",
                json={"template_name": "General"},
            )
        assert multi.status_code == 400
        assert started_workflows == []
    finally:
        await _delete_transcription(ids["transcription_id"])


@pytest.mark.asyncio(loop_scope="session")
async def test_retry_publish_failure_marks_failed(failed_transcription, monkeypatch):
    """A definite enqueue failure leaves the retry explicitly retryable."""
    transcription_id = failed_transcription["transcription_id"]

    async def _boom(_transcription_id, _minute_id):
        msg = "temporal unavailable"
        raise RuntimeError(msg)

    monkeypatch.setattr(
        "backend.api.routes.transcriptions.temporal.start_transcription_workflow",
        _boom,
    )

    async with get_test_client() as ac:
        response = await ac.post(
            f"/transcriptions/{transcription_id}/retry",
            json={"template_name": "General"},
        )

    assert response.status_code == 503
    async with AsyncSession(async_engine) as session:
        transcription = await session.get(Transcription, transcription_id)
        assert transcription.status == JobStatus.FAILED


@pytest.mark.asyncio(loop_scope="session")
async def test_patch_rejected_while_processing(in_progress_transcription, failed_transcription):
    """Finding 2: a PATCH while processing would race the workflow's writes, so it is
    refused until the job is terminal."""
    async with get_test_client() as ac:
        blocked = await ac.patch(
            f"/transcriptions/{in_progress_transcription['transcription_id']}", json={"title": "renamed"}
        )
        allowed = await ac.patch(
            f"/transcriptions/{failed_transcription['transcription_id']}", json={"title": "renamed"}
        )

    assert blocked.status_code == 409
    assert allowed.status_code == 200
    async with AsyncSession(async_engine) as session:
        transcription = await session.get(Transcription, in_progress_transcription["transcription_id"])
        assert transcription.title != "renamed"

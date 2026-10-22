"""Crash-recovery tests for the audio + STT steps (the `prepare_audio` and `transcribe` activities).

Temporal runs one attempt at a time and one workflow per transcription, so an IN_PROGRESS row is
this workflow's own earlier attempt and the retry adopts its claim: a crashed or throttled attempt
is retried straight away, without waiting for the claim to go stale. A genuinely non-transient
failure marks the row FAILED, and the retry then fails again (the user retries via the API).

These call the activities' step functions directly, so they need no Temporal context. Requires the
docker-compose Postgres (`make run`).
"""

import asyncio
import uuid
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from typing import Any, cast

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import async_sessionmaker
from sqlmodel import delete
from sqlmodel.ext.asyncio.session import AsyncSession

from common.database.postgres_database import async_engine
from common.database.postgres_models import Minute, MinuteVersion, Recording, Transcription
from common.runtime import Runtime
from common.services.stt import TranscriptionFailedError, TranscriptionTransientError
from common.types import JobStatus
from common.workflows import transcription as wf
from common.workflows.activities import _shared
from common.workflows.activities import prepare_audio as prepare_activity
from common.workflows.activities import transcribe as transcribe_activity
from tests.utils import get_or_create_user

RECOVERY_EMAIL = "transcription-recovery-test@example.com"
TRANSCRIPT = [{"speaker": "A", "text": "we survived the crash", "start_time": 0.0, "end_time": 1.0}]


async def _current_user_id(session: AsyncSession) -> uuid.UUID:
    return (await get_or_create_user(session, RECOVERY_EMAIL)).id


@pytest_asyncio.fixture
async def transcription_setup() -> dict[str, uuid.UUID]:
    """Transcription -> recording -> minute -> minute_version chain that the worker path expects."""
    ids: dict[str, uuid.UUID] = {}

    async with AsyncSession(async_engine, expire_on_commit=False) as session:
        user_id = await _current_user_id(session)
        transcription = Transcription(user_id=user_id, status=JobStatus.AWAITING_START, error=None)
        session.add(transcription)
        await session.flush()
        recording = Recording(
            user_id=user_id,
            s3_file_key=f"recoverytest/{uuid.uuid4().hex}.mp3",
            transcription_id=transcription.id,
        )
        minute = Minute(template_name="General", transcription_id=transcription.id)
        minute_version = MinuteVersion(minute_id=minute.id, status=JobStatus.AWAITING_START)
        session.add(recording)
        session.add(minute)
        session.add(minute_version)
        await session.commit()
        ids.update(
            transcription_id=transcription.id,
            minute_id=minute.id,
            minute_version_id=minute_version.id,
        )

    yield ids

    async with AsyncSession(async_engine) as session:
        await session.exec(delete(Recording).where(Recording.transcription_id == ids["transcription_id"]))
        await session.exec(delete(MinuteVersion).where(MinuteVersion.id == ids["minute_version_id"]))
        await session.exec(delete(Minute).where(Minute.id == ids["minute_id"]))
        await session.exec(delete(Transcription).where(Transcription.id == ids["transcription_id"]))
        await session.commit()


class _FakeStt:
    """STT whose single call is the test's `transcribe`; the timeout/attempt args pass through."""

    def __init__(self, transcribe) -> None:
        self._transcribe = transcribe

    async def transcribe(self, audio_file_path, timeout_seconds: float = 0.0, attempt: int = 1):
        return await self._transcribe(audio_file_path, timeout_seconds, attempt)


def _stub_stt(monkeypatch, transcribe, *, prepare_fails: Exception | None = None) -> Runtime:
    """Skip download/ffmpeg (both activities' prepare step) and replace the STT call.

    Returns the Runtime the activities run with, so tests pass it to the step functions.
    """

    async def _prepare(transcription, work_dir, storage, db):  # noqa: ARG001
        if prepare_fails:
            raise prepare_fails
        return SimpleNamespace(file_path=work_dir / "audio.mp3", duration_seconds=98.0)

    monkeypatch.setattr(prepare_activity, "prepare_recording", _prepare)
    monkeypatch.setattr(transcribe_activity, "prepare_recording", _prepare)
    monkeypatch.setattr(_shared, "capture_event", lambda *_a, **_k: None)
    return Runtime(
        storage=cast(Any, None),
        stt=_FakeStt(transcribe),
        db=async_sessionmaker(async_engine, expire_on_commit=False),
    )


def _transcribe_input(minute_id: uuid.UUID, timeout_seconds: float = 300) -> wf.TranscribeInput:
    return wf.TranscribeInput(minute_id=str(minute_id), stt_timeout_seconds=timeout_seconds)


async def _transcript(_path, timeout_seconds, attempt):  # noqa: ARG001
    return TRANSCRIPT


async def _status(transcription_id: uuid.UUID) -> Transcription:
    async with AsyncSession(async_engine) as session:
        return await session.get(Transcription, transcription_id)


async def _reassign_claim(transcription_id: uuid.UUID) -> None:
    """Stand in for another owner taking the row over: its fencing token changes."""
    async with AsyncSession(async_engine) as session:
        transcription = await session.get(Transcription, transcription_id)
        transcription.updated_datetime = datetime.now(UTC) + timedelta(minutes=1)
        session.add(transcription)
        await session.commit()


@pytest.mark.asyncio(loop_scope="session")
async def test_prepare_then_transcribe_on_the_next_region(transcription_setup, monkeypatch):
    minute_id = transcription_setup["minute_id"]
    seen: list = []

    async def _stt(_path, timeout_seconds, attempt):
        seen.append((timeout_seconds, attempt))
        return TRANSCRIPT

    runtime = _stub_stt(monkeypatch, _stt)
    prepared = await prepare_activity._prepare_audio(minute_id, runtime)
    assert prepared.duration_seconds == 98.0
    assert (await _status(transcription_setup["transcription_id"])).status == JobStatus.IN_PROGRESS

    # attempt 2: a retry after a throttled first attempt, on the next region
    result = await transcribe_activity._transcribe(_transcribe_input(minute_id), attempt=2, runtime=runtime)
    assert result == str(transcription_setup["transcription_id"])
    assert seen == [(300, 2)]
    row = await _status(transcription_setup["transcription_id"])
    assert row.status == JobStatus.IN_PROGRESS  # COMPLETED is a later activity
    assert row.dialogue_entries == TRANSCRIPT


@pytest.mark.asyncio(loop_scope="session")
async def test_transcribe_crashing_halfway_recovers_on_retry(transcription_setup, monkeypatch):
    minute_id = transcription_setup["minute_id"]
    transcription_id = transcription_setup["transcription_id"]

    async def _crash(_path, timeout_seconds, attempt):  # noqa: ARG001
        raise asyncio.CancelledError  # BaseException: e.g. the SDK cancelling a timed-out attempt

    runtime = _stub_stt(monkeypatch, _crash)
    await prepare_activity._prepare_audio(minute_id, runtime)
    with pytest.raises(asyncio.CancelledError):
        await transcribe_activity._transcribe(_transcribe_input(minute_id), attempt=1, runtime=runtime)
    assert (await _status(transcription_id)).status == JobStatus.IN_PROGRESS

    # The retry adopts the crashed attempt's claim and recovers, without waiting for it to go stale.
    runtime = _stub_stt(monkeypatch, _transcript)
    assert await transcribe_activity._transcribe(_transcribe_input(minute_id), attempt=2, runtime=runtime) == str(
        transcription_id
    )
    assert (await _status(transcription_id)).dialogue_entries == TRANSCRIPT


@pytest.mark.asyncio(loop_scope="session")
async def test_provider_unavailable_leaves_row_for_retry(transcription_setup, monkeypatch):
    """Every region throttled: transient, so the row stays IN_PROGRESS (not FAILED) and the retry succeeds."""
    minute_id = transcription_setup["minute_id"]
    transcription_id = transcription_setup["transcription_id"]

    async def _throttled(_path, timeout_seconds, attempt):  # noqa: ARG001
        msg = "every region 429"
        raise TranscriptionTransientError(msg)

    runtime = _stub_stt(monkeypatch, _throttled)
    await prepare_activity._prepare_audio(minute_id, runtime)
    with pytest.raises(TranscriptionTransientError):
        await transcribe_activity._transcribe(_transcribe_input(minute_id), attempt=1, runtime=runtime)
    row = await _status(transcription_id)
    assert row.status == JobStatus.IN_PROGRESS
    assert row.error is None

    runtime = _stub_stt(monkeypatch, _transcript)
    assert await transcribe_activity._transcribe(_transcribe_input(minute_id), attempt=2, runtime=runtime) == str(
        transcription_id
    )


@pytest.mark.asyncio(loop_scope="session")
@pytest.mark.parametrize("step", ["prepare", "transcribe"])
async def test_handled_failure_marks_failed_and_is_not_retried(transcription_setup, monkeypatch, step):
    """A non-transient error (corrupt audio, 400 from Azure) is HANDLED: the row goes FAILED and a
    retry raises again (FAILED is terminal; the user retries via the API instead)."""
    minute_id = transcription_setup["minute_id"]
    boom = RuntimeError("provider exploded")

    async def _fail(_path, timeout_seconds, attempt):  # noqa: ARG001
        raise boom

    if step == "prepare":
        runtime = _stub_stt(monkeypatch, _transcript, prepare_fails=boom)
        with pytest.raises(TranscriptionFailedError):
            await prepare_activity._prepare_audio(minute_id, runtime)
        with pytest.raises(TranscriptionFailedError):
            await prepare_activity._prepare_audio(minute_id, runtime)
    else:
        runtime = _stub_stt(monkeypatch, _fail)
        await prepare_activity._prepare_audio(minute_id, runtime)
        with pytest.raises(TranscriptionFailedError):
            await transcribe_activity._transcribe(_transcribe_input(minute_id), attempt=1, runtime=runtime)
        with pytest.raises(TranscriptionFailedError):
            await transcribe_activity._transcribe(_transcribe_input(minute_id), attempt=2, runtime=runtime)
    row = await _status(transcription_setup["transcription_id"])
    assert row.status == JobStatus.FAILED
    assert "provider exploded" in row.error


@pytest.mark.asyncio(loop_scope="session")
async def test_failure_persist_error_is_not_swallowed(transcription_setup, monkeypatch):
    """If recording FAILED itself fails, the error escapes as UNHANDLED (retryable), so the
    row is not stranded IN_PROGRESS behind a non-retryable failure."""

    async def _fail(_path, timeout_seconds, attempt):  # noqa: ARG001
        msg = "provider exploded"
        raise RuntimeError(msg)

    runtime = _stub_stt(monkeypatch, _fail)
    await prepare_activity._prepare_audio(transcription_setup["minute_id"], runtime)

    async def _persist_fails(*_args, **_kwargs):
        msg = "database down"
        raise RuntimeError(msg)

    monkeypatch.setattr(_shared, "fenced_update", _persist_fails)
    with pytest.raises(RuntimeError, match="database down"):
        await transcribe_activity._transcribe(
            _transcribe_input(transcription_setup["minute_id"]), attempt=1, runtime=runtime
        )


@pytest.mark.asyncio(loop_scope="session")
async def test_superseded_attempt_cannot_write(transcription_setup, monkeypatch):
    """An attempt whose claim was taken over has its late write dropped instead of clobbering the
    new owner: the fenced write fails and the step raises Transient so Temporal retries."""
    minute_id = transcription_setup["minute_id"]
    transcription_id = transcription_setup["transcription_id"]

    async def _stalls_then_returns(_path, timeout_seconds, attempt):  # noqa: ARG001
        await _reassign_claim(transcription_id)  # another owner takes the row over mid-call
        return TRANSCRIPT

    runtime = _stub_stt(monkeypatch, _stalls_then_returns)
    await prepare_activity._prepare_audio(minute_id, runtime)
    with pytest.raises(TranscriptionTransientError):
        await transcribe_activity._transcribe(_transcribe_input(minute_id), attempt=1, runtime=runtime)
    assert (await _status(transcription_id)).dialogue_entries is None

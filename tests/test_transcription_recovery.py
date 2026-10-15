"""End-to-end recovery test for a transcription that fails halfway.

Delivery 1: process_transcription claims the job (AWAITING_START -> IN_PROGRESS),
then dies mid-provider-call via CancelledError, which escapes the handled-failure
path (that path would write FAILED and complete the message) and leaves the row
claimed but unfinished.

Delivery 2 (SQS redelivered the message after the visibility timeout): the claim is
stale, so process_transcription reclaims it, re-runs the provider and completes.

Requires the docker-compose Postgres (`make run`).
"""

import asyncio
import uuid
from datetime import UTC, datetime, timedelta

import pytest
import pytest_asyncio
from sqlmodel import delete
from sqlmodel.ext.asyncio.session import AsyncSession

from common.database.postgres_database import async_engine
from common.database.postgres_models import (
    JobStatus,
    Minute,
    MinuteVersion,
    Recording,
    Transcription,
)
from common.services.exceptions import TranscriptionFailedError
from common.services.transcription_handler_service import TranscriptionHandlerService
from common.settings import CLAIM_STALE_AFTER
from common.types import TranscriptionJobMessageData
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


@pytest.mark.asyncio(loop_scope="session")
async def test_job_crashing_halfway_recovers_on_redelivery(transcription_setup, monkeypatch):
    minute_id = transcription_setup["minute_id"]
    transcription_id = transcription_setup["transcription_id"]

    # Delivery 1: the worker claims the job, then dies before the provider returns.
    async def _crash(transcription):  # noqa: ARG001
        raise asyncio.CancelledError  # BaseException: survives the handler's except block

    monkeypatch.setattr(
        "common.services.transcription_handler_service.transcription_manager.perform_transcription_steps", _crash
    )
    with pytest.raises(asyncio.CancelledError):
        await TranscriptionHandlerService.process_transcription(minute_id=minute_id)

    async with AsyncSession(async_engine) as session:
        transcription = await session.get(Transcription, transcription_id)
        assert transcription.status == JobStatus.IN_PROGRESS
        claimed_at = transcription.updated_datetime

    # Simulate the outage passing: the crashed claim ages past CLAIM_STALE_AFTER
    new_time = datetime.now(UTC) - CLAIM_STALE_AFTER - timedelta(minutes=5)
    async with AsyncSession(async_engine) as session:
        transcription = await session.get(Transcription, transcription_id)
        transcription.updated_datetime = new_time
        session.add(transcription)
        await session.commit()

    assert claimed_at > new_time

    # Delivery 2: SQS redelivers the message; the stale claim is reclaimed and the job completes.
    async def _recover(transcription):  # noqa: ARG001
        return TranscriptionJobMessageData(transcription_service="MockAdapter", transcript=TRANSCRIPT)

    async def _speak(entries):
        return entries

    monkeypatch.setattr(
        "common.services.transcription_handler_service.transcription_manager.perform_transcription_steps", _recover
    )
    monkeypatch.setattr("common.services.transcription_handler_service.process_speakers_and_dialogue_entries", _speak)

    async def _fake_title(transcript):  # noqa: ARG001
        return "Recovered meeting"

    monkeypatch.setattr("common.services.transcription_handler_service.generate_meeting_title", _fake_title)
    monkeypatch.setattr("common.services.transcription_handler_service.capture_event", lambda *_args, **_kwargs: None)

    transcription_job = await TranscriptionHandlerService.process_transcription(minute_id=minute_id)

    assert transcription_job.transcript == TRANSCRIPT
    async with AsyncSession(async_engine) as session:
        transcription = await session.get(Transcription, transcription_id)
        assert transcription.status == JobStatus.COMPLETED
        assert transcription.dialogue_entries == TRANSCRIPT
        assert transcription.title == "Recovered meeting"


@pytest.mark.asyncio(loop_scope="session")
async def test_handled_failure_marks_failed_and_stops_redelivery_transcription(transcription_setup, monkeypatch):
    """A normal exception is a HANDLED failure: row goes FAILED and the message completes,
    so a redelivery must not re-run the provider (the user retries via the API instead)."""
    minute_id = transcription_setup["minute_id"]
    transcription_id = transcription_setup["transcription_id"]

    calls = {"n": 0}

    async def _fail(transcription):  # noqa: ARG001
        provider_error = "provider exploded"
        raise RuntimeError(provider_error)

    async def _count_provider(transcription):
        calls["n"] += 1
        await _fail(transcription)

    monkeypatch.setattr(
        "common.services.transcription_handler_service.transcription_manager.perform_transcription_steps",
        _count_provider,
    )
    with pytest.raises(TranscriptionFailedError):
        await TranscriptionHandlerService.process_transcription(minute_id=minute_id)

    async with AsyncSession(async_engine) as session:
        transcription = await session.get(Transcription, transcription_id)
        assert transcription.status == JobStatus.FAILED
        assert transcription.error

    # redelivery: FAILED is never claimable, so the provider must not run again
    monkeypatch.setattr(
        "common.services.transcription_handler_service.transcription_manager.perform_transcription_steps", _fail
    )
    assert await TranscriptionHandlerService.process_transcription(minute_id=minute_id) is None
    assert calls["n"] == 1


@pytest.mark.asyncio(loop_scope="session")
async def test_duplicate_async_poll_delivery_is_fenced(transcription_setup):
    """A duplicate poll carries the active claim token and cannot create a new claim."""
    transcription_id = transcription_setup["transcription_id"]
    token = TranscriptionHandlerService.claim_transcription(transcription_id)
    assert token is not None
    assert TranscriptionHandlerService.claim_transcription(transcription_id) is None


@pytest.mark.asyncio(loop_scope="session")
async def test_failure_persist_error_is_not_swallowed(transcription_setup, monkeypatch):
    """Finding 6: if recording FAILED fails, the error must escape as UNHANDLED so the
    worker does not acknowledge the message and strand the row with no recovery delivery."""
    minute_id = transcription_setup["minute_id"]

    async def _provider_fails(_transcription):
        msg = "provider exploded"
        raise RuntimeError(msg)

    monkeypatch.setattr(
        "common.services.transcription_handler_service.transcription_manager.perform_transcription_steps",
        _provider_fails,
    )

    def _persist_fails(*_args, **_kwargs):
        msg = "database down"
        raise RuntimeError(msg)

    monkeypatch.setattr(TranscriptionHandlerService, "update_transcription", _persist_fails)

    # RuntimeError (not the handled TranscriptionFailedError the actor acknowledges)
    with pytest.raises(RuntimeError):
        await TranscriptionHandlerService.process_transcription(minute_id=minute_id)


async def _age_claim(transcription_id: uuid.UUID) -> None:
    async with AsyncSession(async_engine) as session:
        transcription = await session.get(Transcription, transcription_id)
        transcription.updated_datetime = datetime.now(UTC) - CLAIM_STALE_AFTER - timedelta(minutes=5)
        session.add(transcription)
        await session.commit()


def _stub_completion(monkeypatch, deleted: list[str]) -> None:
    async def _check(adapter_name, async_transcription_message_data):  # noqa: ARG001
        return async_transcription_message_data.model_copy(
            update={"transcript": TRANSCRIPT, "transcript_key": "restricted/transcribe-output/x/out.json"}
        )

    async def _same(entries):
        return entries

    async def _title(transcript):  # noqa: ARG001
        return "Recovered poll"

    async def _delete(key):
        deleted.append(key)

    module = "common.services.transcription_handler_service"
    monkeypatch.setattr(f"{module}.transcription_manager.check_transcription", _check)
    monkeypatch.setattr(f"{module}.process_speakers_and_dialogue_entries", _same)
    monkeypatch.setattr(f"{module}.generate_meeting_title", _title)
    monkeypatch.setattr(f"{module}.capture_event", lambda *_a, **_k: None)
    monkeypatch.setattr(f"{module}.storage_service.delete", _delete)


@pytest.mark.asyncio(loop_scope="session")
async def test_superseded_poll_token_reclaims_abandoned_job(transcription_setup, monkeypatch):
    """Finding 1: a poll worker that crashed after rotating the token leaves the
    redelivered message with a dead token. Once the claim is stale it must reclaim,
    complete, and only then delete the provider output (finding 3)."""
    transcription_id = transcription_setup["transcription_id"]
    old_token = TranscriptionHandlerService.claim_transcription(transcription_id)
    assert old_token is not None
    await _age_claim(transcription_id)  # row now ages past the stale window; old_token no longer matches

    deleted: list[str] = []
    _stub_completion(monkeypatch, deleted)
    message = TranscriptionJobMessageData(transcription_service="AWSTranscribe", job_name="j", claim_token=old_token)

    job = await TranscriptionHandlerService.process_transcription(
        minute_id=transcription_setup["minute_id"], async_transcription_message_data=message
    )

    assert job is not None
    assert deleted == ["restricted/transcribe-output/x/out.json"]
    async with AsyncSession(async_engine) as session:
        transcription = await session.get(Transcription, transcription_id)
        assert transcription.status == JobStatus.COMPLETED
        assert transcription.dialogue_entries == TRANSCRIPT


@pytest.mark.asyncio(loop_scope="session")
async def test_superseded_poll_token_cannot_steal_live_or_fresh_job(transcription_setup, monkeypatch):
    """A dead-token poll must not take a live claim, nor start a fresh AWAITING_START job."""
    transcription_id = transcription_setup["transcription_id"]
    deleted: list[str] = []
    _stub_completion(monkeypatch, deleted)
    message = TranscriptionJobMessageData(
        transcription_service="AWSTranscribe", job_name="j", claim_token=datetime.now(UTC) - timedelta(days=1)
    )

    # AWAITING_START (e.g. just retried): not claimable by a poll message
    assert (
        await TranscriptionHandlerService.process_transcription(
            minute_id=transcription_setup["minute_id"], async_transcription_message_data=message
        )
        is None
    )
    # live IN_PROGRESS claim: not claimable either
    assert TranscriptionHandlerService.claim_transcription(transcription_id) is not None
    assert (
        await TranscriptionHandlerService.process_transcription(
            minute_id=transcription_setup["minute_id"], async_transcription_message_data=message
        )
        is None
    )
    assert deleted == []


@pytest.mark.asyncio(loop_scope="session")
async def test_provider_output_kept_when_write_superseded(transcription_setup, monkeypatch):
    """Finding 3: if the COMPLETED write is rejected, the provider output must survive
    so the current owner can still read it."""
    token = TranscriptionHandlerService.claim_transcription(transcription_setup["transcription_id"])
    deleted: list[str] = []
    _stub_completion(monkeypatch, deleted)
    monkeypatch.setattr(TranscriptionHandlerService, "update_transcription", lambda *_a, **_k: False)
    message = TranscriptionJobMessageData(transcription_service="AWSTranscribe", job_name="j", claim_token=token)

    assert (
        await TranscriptionHandlerService.process_transcription(
            minute_id=transcription_setup["minute_id"], async_transcription_message_data=message
        )
        is None
    )
    assert deleted == []


@pytest.mark.asyncio(loop_scope="session")
async def test_provider_output_delete_failure_does_not_fail_job(transcription_setup, monkeypatch):
    token = TranscriptionHandlerService.claim_transcription(transcription_setup["transcription_id"])
    _stub_completion(monkeypatch, [])

    async def _boom(_key):
        msg = "s3 down"
        raise RuntimeError(msg)

    monkeypatch.setattr("common.services.transcription_handler_service.storage_service.delete", _boom)
    message = TranscriptionJobMessageData(transcription_service="AWSTranscribe", job_name="j", claim_token=token)

    assert (
        await TranscriptionHandlerService.process_transcription(
            minute_id=transcription_setup["minute_id"], async_transcription_message_data=message
        )
        is not None
    )
    async with AsyncSession(async_engine) as session:
        transcription = await session.get(Transcription, transcription_setup["transcription_id"])
        assert transcription.status == JobStatus.COMPLETED

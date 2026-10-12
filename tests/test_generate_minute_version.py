"""Workflow-level idempotency, failure handling and recovery for the MINUTE pipeline.

These drive the real two-level claim against a reachable Postgres while stubbing the
transcription/LLM actions, so they are deterministic and offline. They pin the
recovery-critical behaviours:

- a COMPLETED transcription skips the expensive transcription phase (no re-STT);
- a second attempt on a COMPLETED version is a no-op (no recompose);
- a transcription-phase failure is recorded and never advances to compose;
- a fresh claim owned elsewhere reports "rehide" (back off, retry later).

Together with tests/test_repository.py (the claim CAS matrix) these cover the
idempotency/recovery guarantees end to end, without paying for Azure/Gemini.
"""

import asyncio
from types import SimpleNamespace
from uuid import uuid4

import pytest

from common.database.postgres_database import AsyncSessionLocal
from common.database.postgres_models import JobStatus, Minute, MinuteVersion, Transcription
from common.database.repository import ClaimState, claim_transcription_for_processing
from worker.workflows import generate_minute_version as workflow

STALE_SECONDS = 600


async def _make_job(
    transcription_status: JobStatus = JobStatus.AWAITING_START,
    version_status: JobStatus = JobStatus.AWAITING_START,
) -> tuple[Transcription, MinuteVersion]:
    async with AsyncSessionLocal() as session:
        transcription = Transcription(id=uuid4(), status=transcription_status)
        minute = Minute(id=uuid4(), transcription_id=transcription.id)
        version = MinuteVersion(id=uuid4(), minute_id=minute.id, status=version_status)
        session.add(transcription)
        session.add(minute)
        session.add(version)
        await session.commit()
        return transcription, version


async def _delete_transcription(transcription_id) -> None:
    async with AsyncSessionLocal() as session:
        transcription = await session.get(Transcription, transcription_id)
        if transcription:
            await session.delete(transcription)
            await session.commit()


async def _version_status(version_id) -> JobStatus:
    async with AsyncSessionLocal() as session:
        version = await session.get(MinuteVersion, version_id)
        assert version is not None
        return version.status


async def _transcription_status(transcription_id) -> JobStatus:
    async with AsyncSessionLocal() as session:
        transcription = await session.get(Transcription, transcription_id)
        assert transcription is not None
        return transcription.status


@pytest.fixture(autouse=True)
def silence_posthog(monkeypatch):
    monkeypatch.setattr(workflow, "capture_event", lambda *_args, **_kwargs: None)


def _run(version_id):
    return workflow.generate_minute_version(version_id, asyncio.Semaphore(1), asyncio.Semaphore(1), STALE_SECONDS)


@pytest.mark.asyncio(loop_scope="session")
async def test_completed_transcription_skips_stt_and_only_composes(monkeypatch):
    """Idempotency: a COMPLETED transcription never re-runs STT — it goes straight to compose."""
    calls = {"transcribe": 0, "compose": 0}

    class CountingSTT:
        async def transcribe(self, _path):
            calls["transcribe"] += 1
            return []

    async def fake_compose(_minute):
        calls["compose"] += 1
        return "<p>ok</p>"

    monkeypatch.setattr(workflow, "transcription_service", CountingSTT())
    monkeypatch.setattr(workflow, "compose_minutes", fake_compose)

    transcription, version = await _make_job(transcription_status=JobStatus.COMPLETED)
    try:
        outcome = await _run(version.id)
        assert outcome == "delete"
        assert calls == {"transcribe": 0, "compose": 1}
        assert await _version_status(version.id) == JobStatus.COMPLETED
    finally:
        await _delete_transcription(transcription.id)


@pytest.mark.asyncio(loop_scope="session")
async def test_completed_version_is_not_recomposed(monkeypatch):
    """Idempotency: a re-delivered job for a COMPLETED version is a no-op (no second LLM call)."""
    calls = {"compose": 0}

    async def fake_compose(_minute):
        calls["compose"] += 1
        return "<p>ok</p>"

    monkeypatch.setattr(workflow, "compose_minutes", fake_compose)

    transcription, version = await _make_job(
        transcription_status=JobStatus.COMPLETED, version_status=JobStatus.COMPLETED
    )
    try:
        outcome = await _run(version.id)
        assert outcome == "delete"
        assert calls["compose"] == 0
    finally:
        await _delete_transcription(transcription.id)


@pytest.mark.asyncio(loop_scope="session")
async def test_transcription_failure_is_recorded_and_never_composes(monkeypatch):
    """Failure handling: a transcription-phase error records FAILED and the job does NOT
    advance to compose (the outcome is "delete" — the user retries from the UI)."""
    calls = {"compose": 0}

    class FailingSTT:
        async def transcribe(self, _path):
            msg = "stt boom"
            raise RuntimeError(msg)

    async def fake_prepare(_transcription, work_dir):
        return SimpleNamespace(file_path=work_dir / "audio.mp3")

    async def fake_compose(_minute):
        calls["compose"] += 1
        return "<p>ok</p>"

    monkeypatch.setattr(workflow, "transcription_service", FailingSTT())
    monkeypatch.setattr(workflow, "prepare_audio", fake_prepare)
    monkeypatch.setattr(workflow, "compose_minutes", fake_compose)

    transcription, version = await _make_job()
    try:
        outcome = await _run(version.id)
        assert outcome == "delete"
        assert calls["compose"] == 0
        assert await _transcription_status(transcription.id) == JobStatus.FAILED
    finally:
        await _delete_transcription(transcription.id)


@pytest.mark.asyncio(loop_scope="session")
async def test_compose_failure_fails_the_version_not_the_transcription(monkeypatch):
    """Failure isolation: a compose-phase error fails the VERSION and leaves the
    transcription COMPLETED (so its transcript is kept and only the minute needs a retry)."""

    async def failing_compose(_minute):
        msg = "compose boom"
        raise RuntimeError(msg)

    monkeypatch.setattr(workflow, "compose_minutes", failing_compose)

    transcription, version = await _make_job(transcription_status=JobStatus.COMPLETED)
    try:
        assert await _run(version.id) == "delete"
        assert await _version_status(version.id) == JobStatus.FAILED
        assert await _transcription_status(transcription.id) == JobStatus.COMPLETED
    finally:
        await _delete_transcription(transcription.id)


@pytest.mark.asyncio(loop_scope="session")
async def test_fresh_claim_owned_elsewhere_rehides():
    """Recovery: while another worker holds a fresh lease the job is not stolen — the
    workflow reports "rehide" so the consumer backs off and retries later."""
    transcription, version = await _make_job()
    try:
        async with AsyncSessionLocal() as session:
            claimed = await claim_transcription_for_processing(session, transcription.id, STALE_SECONDS)
            await session.commit()
        assert claimed == ClaimState.CLAIMED

        assert await _run(version.id) == "rehide"
    finally:
        await _delete_transcription(transcription.id)

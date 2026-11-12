"""Failure finalisation must include jobs that never reached their initial claim."""

from unittest.mock import Mock

import pytest
from sqlmodel.ext.asyncio.session import AsyncSession

from common.database.postgres_database import async_engine
from common.database.postgres_models import JobStatus, Transcription
from common.services.exceptions import TranscriptionFailedError
from common.workflows.activities import _shared


@pytest.mark.asyncio(loop_scope="session")
@pytest.mark.parametrize("status", list(JobStatus))
async def test_transcription_failure_finalises_only_unfinished_rows(minute_version_setup, status, monkeypatch):
    monkeypatch.setattr(_shared, "capture_event", lambda *_args: None)
    transcription_id = minute_version_setup["transcription_id"]
    async with AsyncSession(async_engine, expire_on_commit=False) as session:
        row = await session.get(Transcription, transcription_id)
        row.status = status
        row.error = "original error"
        await session.commit()
    result = _shared.mark_failed(row, "database unavailable")
    unfinished = status in (JobStatus.AWAITING_START, JobStatus.IN_PROGRESS)
    assert (result is not None) is unfinished
    async with AsyncSession(async_engine) as session:
        saved = await session.get(Transcription, transcription_id)
        assert saved.status == (JobStatus.FAILED if unfinished else status)
        assert saved.error == ("Transcription failed: database unavailable" if unfinished else "original error")


@pytest.mark.asyncio(loop_scope="session")
async def test_provider_failures_record_failure_event(minute_version_setup, monkeypatch):
    """Verifies that provider failures retain the ordinary failure event."""
    capture_event = Mock()
    monkeypatch.setattr(_shared, "capture_event", capture_event)
    transcription_id = minute_version_setup["transcription_id"]
    async with AsyncSession(async_engine, expire_on_commit=False) as session:
        row = await session.get(Transcription, transcription_id)
        row.status = JobStatus.IN_PROGRESS
        await session.commit()
    assert _shared.mark_failed(row, TranscriptionFailedError("No transcription phrases found in response"))
    async with AsyncSession(async_engine) as session:
        saved = await session.get(Transcription, transcription_id)
        assert saved.status == JobStatus.FAILED
    capture_event.assert_called_once_with(row.user_id, "transcription_failed", {"transcriptionId": str(row.id)})

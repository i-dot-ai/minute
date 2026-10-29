"""Failure finalisation must include jobs that never reached their initial claim."""

import pytest
from sqlmodel.ext.asyncio.session import AsyncSession

from common.database.postgres_database import async_engine
from common.database.postgres_models import JobStatus, Transcription
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

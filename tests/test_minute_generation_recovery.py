"""End-to-end recovery test for a MINUTE GENERATION that fails halfway.

First attempt: process_minute_generation_message moves the version to IN_PROGRESS then dies
mid-generation via CancelledError, which escapes its handled-failure block (that writes FAILED),
exactly like an unexpected worker crash.

Retry: Temporal retries the activity straight away; the row is still IN_PROGRESS (ours), so the
generation runs to completion. No staleness wait is involved.

Requires the docker-compose Postgres (`make run`).
"""

import asyncio
import uuid

import pytest
import pytest_asyncio
from sqlmodel import delete, select
from sqlmodel.ext.asyncio.session import AsyncSession

from common.database.postgres_database import async_engine
from common.database.postgres_models import (
    JobStatus,
    Minute,
    MinuteVersion,
    Transcription,
    User,
)
from common.services.minute_handler_service import MinuteGenerationFailedError, MinuteHandlerService
from common.types import MeetingType
from tests.utils import get_or_create_user

RECOVERY_EMAIL = "minute-recovery-test@example.com"


async def _current_user_id(session: AsyncSession) -> uuid.UUID:
    return (await get_or_create_user(session, RECOVERY_EMAIL)).id


@pytest_asyncio.fixture
async def minute_version_setup() -> dict[str, uuid.UUID]:
    ids: dict[str, uuid.UUID] = {}

    async with AsyncSession(async_engine, expire_on_commit=False) as session:
        user_id = await _current_user_id(session)
        transcription = Transcription(
            user_id=user_id,
            status=JobStatus.COMPLETED,
            dialogue_entries=[{"speaker": "A", "text": "hello", "start_time": 0.0, "end_time": 1.0}],
        )
        minute = Minute(template_name="General", transcription_id=transcription.id)
        minute_version = MinuteVersion(minute_id=minute.id, status=JobStatus.AWAITING_START)
        session.add(transcription)
        session.add(minute)
        session.add(minute_version)
        await session.commit()
        ids.update(transcription_id=transcription.id, minute_id=minute.id, minute_version_id=minute_version.id)

    yield ids

    async with AsyncSession(async_engine) as session:
        await session.exec(delete(MinuteVersion).where(MinuteVersion.id == ids["minute_version_id"]))
        await session.exec(delete(Minute).where(Minute.id == ids["minute_id"]))
        await session.exec(delete(Transcription).where(Transcription.id == ids["transcription_id"]))
        await session.commit()


@pytest.mark.asyncio(loop_scope="session")
async def test_minute_generation_crashing_halfway_recovers_on_retry(minute_version_setup, monkeypatch):
    minute_version_id = minute_version_setup["minute_version_id"]

    # Force the too_short path so generation stays LLM-free on the retry.
    monkeypatch.setattr(
        MinuteHandlerService, "predict_meeting", classmethod(lambda _cls, _entries: MeetingType.too_short)
    )
    monkeypatch.setattr("common.services.minute_handler_service.capture_event", lambda *_args, **_kwargs: None)

    # First attempt: generation dies like an unexpected worker crash would.
    real_generate_minutes = MinuteHandlerService.generate_minutes.__func__

    async def _crash(cls, meeting_type, minute):  # noqa: ARG001
        raise asyncio.CancelledError  # BaseException: survives the handler's except block

    monkeypatch.setattr(MinuteHandlerService, "generate_minutes", classmethod(_crash))
    with pytest.raises(asyncio.CancelledError):
        await MinuteHandlerService.process_minute_generation_message(minute_version_id)

    async with AsyncSession(async_engine) as session:
        assert (await session.get(MinuteVersion, minute_version_id)).status == JobStatus.IN_PROGRESS

    # Temporal's retry: the IN_PROGRESS row is this workflow's own earlier attempt.
    monkeypatch.setattr(MinuteHandlerService, "generate_minutes", classmethod(real_generate_minutes))
    await MinuteHandlerService.process_minute_generation_message(minute_version_id)

    async with AsyncSession(async_engine) as session:
        minute_version = await session.get(MinuteVersion, minute_version_id)
        assert minute_version.status == JobStatus.COMPLETED
        # too_short generation runs through mistune.html, hence the <p> wrapper
        assert "Short meeting detected" in minute_version.html_content


@pytest.mark.asyncio(loop_scope="session")
async def test_edit_rejects_cross_user_source(minute_version_setup, monkeypatch):
    """Worker-side half of minute_4996 vuln-0002: process_minute_edit_message must
    refuse a source version owned by a different user than the target."""
    target_version_id = minute_version_setup["minute_version_id"]

    async with AsyncSession(async_engine, expire_on_commit=False) as session:
        foreign_user = (await session.exec(select(User).where(User.email == "minute-edit-foreign@example.com"))).first()
        if foreign_user is None:
            foreign_user = User(email="minute-edit-foreign@example.com")
            session.add(foreign_user)
            await session.flush()
        foreign_transcription = Transcription(user_id=foreign_user.id, status=JobStatus.COMPLETED)
        session.add(foreign_transcription)
        await session.flush()
        foreign_minute = Minute(template_name="General", transcription_id=foreign_transcription.id)
        session.add(foreign_minute)
        await session.flush()
        foreign_version = MinuteVersion(minute_id=foreign_minute.id, status=JobStatus.COMPLETED)
        session.add(foreign_version)
        await session.commit()
        foreign_ids = (foreign_transcription.id, foreign_minute.id, foreign_version.id)

    async def _ai_edit(cls, *_args, **_kwargs):  # noqa: ARG001
        msg = "LLM must not be called for a cross-user edit"
        raise AssertionError(msg)

    monkeypatch.setattr(MinuteHandlerService, "edit_minutes_with_ai", classmethod(_ai_edit))

    try:
        with pytest.raises(MinuteGenerationFailedError):
            await MinuteHandlerService.process_minute_edit_message(
                source_minute_version_id=foreign_version.id,
                target_minute_version_id=target_version_id,
            )
    finally:
        async with AsyncSession(async_engine) as session:
            await session.exec(delete(MinuteVersion).where(MinuteVersion.id == foreign_ids[2]))
            await session.exec(delete(Minute).where(Minute.id == foreign_ids[1]))
            await session.exec(delete(Transcription).where(Transcription.id == foreign_ids[0]))
            await session.commit()

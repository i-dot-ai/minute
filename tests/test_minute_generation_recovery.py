"""End-to-end recovery test for a MINUTE GENERATION that fails halfway.

Delivery 1: process_minute_generation_message claims the version (AWAITING_START ->
IN_PROGRESS) then dies mid-generation via CancelledError, which escapes its handled-
failure block (that writes FAILED) and leaves the claim stale, exactly like an
unexpected worker crash.

Delivery 2: the redelivered message reclaims the stale claim and completes the version.

Requires the docker-compose Postgres (`make run`).
"""

import asyncio
import uuid
from datetime import UTC, datetime, timedelta

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
from common.services.minute_handler_service import MinuteHandlerService
from common.settings import CLAIM_STALE_AFTER
from common.types import MeetingType

RECOVERY_EMAIL = "minute-recovery-test@example.com"


async def _current_user_id(session: AsyncSession) -> uuid.UUID:
    user = (await session.exec(select(User).where(User.email == RECOVERY_EMAIL))).first()
    if user is None:
        user = User(email=RECOVERY_EMAIL)
        session.add(user)
        await session.commit()
        await session.refresh(user)
    return user.id


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
async def test_minute_generation_crashing_halfway_recovers_on_redelivery(minute_version_setup, monkeypatch):
    minute_version_id = minute_version_setup["minute_version_id"]

    # Force the too_short path so generation stays LLM-free on the recovery delivery.
    monkeypatch.setattr(
        MinuteHandlerService, "predict_meeting", classmethod(lambda _cls, _entries: MeetingType.too_short)
    )

    # Delivery 1: claim happens, generation dies like an unexpected worker crash would.
    real_generate_minutes = MinuteHandlerService.generate_minutes.__func__

    async def _crash(cls, meeting_type, minute):  # noqa: ARG001
        raise asyncio.CancelledError  # BaseException: survives the handler's except block

    monkeypatch.setattr(MinuteHandlerService, "generate_minutes", classmethod(_crash))
    monkeypatch.setattr("common.services.minute_handler_service.capture_event", lambda *_args, **_kwargs: None)
    with pytest.raises(asyncio.CancelledError):
        await MinuteHandlerService.process_minute_generation_message(minute_version_id)

    async with AsyncSession(async_engine) as session:
        minute_version = await session.get(MinuteVersion, minute_version_id)
        assert minute_version.status == JobStatus.IN_PROGRESS
        generated_at = minute_version.updated_datetime

    # Simulate the outage passing: the crashed claim ages past CLAIM_STALE_AFTER.
    stale_time = datetime.now(UTC) - CLAIM_STALE_AFTER - timedelta(minutes=5)
    async with AsyncSession(async_engine) as session:
        minute_version = await session.get(MinuteVersion, minute_version_id)
        minute_version.updated_datetime = stale_time
        session.add(minute_version)
        await session.commit()

    assert generated_at > stale_time

    # Delivery 2: reclaims the stale claim and finishes generation (too_short = no LLM).
    monkeypatch.setattr(MinuteHandlerService, "generate_minutes", classmethod(real_generate_minutes))
    await MinuteHandlerService.process_minute_generation_message(minute_version_id)

    async with AsyncSession(async_engine) as session:
        minute_version = await session.get(MinuteVersion, minute_version_id)
        assert minute_version.status == JobStatus.COMPLETED
        # too_short generation runs through mistune.html, hence the <p> wrapper
        assert "Short meeting detected" in minute_version.html_content
        assert minute_version.updated_datetime > stale_time

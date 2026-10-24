"""Tests for TranscriptionHandlerService.reconcile_duplicate_delivery.

Findings 4 and 5: a delivery that loses the claim must be acknowledged only when the
job is terminal, and a completed transcription whose minute generation message never
landed must be healed on redelivery.

Requires the docker-compose Postgres (`make run`).
"""

import uuid

import pytest
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
from common.services.transcription_handler_service import DuplicateDelivery, TranscriptionHandlerService
from tests.utils import get_or_create_user

EMAIL = "duplicate-delivery-test@example.com"


async def _seed(transcription_status: JobStatus, version_status: JobStatus) -> dict[str, uuid.UUID]:
    async with AsyncSession(async_engine, expire_on_commit=False) as session:
        user = await get_or_create_user(session, EMAIL)
        transcription = Transcription(user_id=user.id, status=transcription_status)
        session.add(transcription)
        await session.flush()
        recording = Recording(
            user_id=user.id, s3_file_key=f"dupdelivery/{uuid.uuid4().hex}.mp3", transcription_id=transcription.id
        )
        minute = Minute(template_name="General", transcription_id=transcription.id)
        session.add(recording)
        session.add(minute)
        await session.flush()
        version = MinuteVersion(minute_id=minute.id, status=version_status)
        session.add(version)
        await session.commit()
        return {"transcription_id": transcription.id, "minute_id": minute.id, "version_id": version.id}


async def _cleanup(ids: dict[str, uuid.UUID]) -> None:
    async with AsyncSession(async_engine) as session:
        await session.exec(delete(Recording).where(Recording.transcription_id == ids["transcription_id"]))
        await session.exec(delete(MinuteVersion).where(MinuteVersion.id == ids["version_id"]))
        await session.exec(delete(Minute).where(Minute.id == ids["minute_id"]))
        await session.exec(delete(Transcription).where(Transcription.id == ids["transcription_id"]))
        await session.commit()


@pytest.mark.asyncio(loop_scope="session")
async def test_completed_with_unqueued_version_republishes_minute():
    ids = await _seed(JobStatus.COMPLETED, JobStatus.AWAITING_START)
    try:
        action = TranscriptionHandlerService.reconcile_duplicate_delivery(ids["minute_id"])
        assert action == DuplicateDelivery.REPUBLISH_MINUTE
    finally:
        await _cleanup(ids)


@pytest.mark.asyncio(loop_scope="session")
async def test_completed_with_started_version_is_acked():
    ids = await _seed(JobStatus.COMPLETED, JobStatus.IN_PROGRESS)
    try:
        action = TranscriptionHandlerService.reconcile_duplicate_delivery(ids["minute_id"])
        assert action == DuplicateDelivery.ACK
    finally:
        await _cleanup(ids)


@pytest.mark.asyncio(loop_scope="session")
async def test_failed_is_acked():
    ids = await _seed(JobStatus.FAILED, JobStatus.AWAITING_START)
    try:
        action = TranscriptionHandlerService.reconcile_duplicate_delivery(ids["minute_id"])
        assert action == DuplicateDelivery.ACK
    finally:
        await _cleanup(ids)


@pytest.mark.asyncio(loop_scope="session")
async def test_in_progress_is_left_for_recovery():
    ids = await _seed(JobStatus.IN_PROGRESS, JobStatus.AWAITING_START)
    try:
        action = TranscriptionHandlerService.reconcile_duplicate_delivery(ids["minute_id"])
        assert action == DuplicateDelivery.LEAVE
    finally:
        await _cleanup(ids)

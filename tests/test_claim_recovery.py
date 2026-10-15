"""Tests for the crash-recovery semantics of claim_transcription and claim_minute_version.

A live claim (fresh IN_PROGRESS) must not be stealable; a stale claim (older than
CLAIM_STALE_AFTER, i.e. the claiming worker died) must be reclaimable, resetting
the age timer so a duplicate delivery after a reclaim stays a no-op.

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
from common.services.job_claim import JobClaimRenewer
from common.services.minute_handler_service import MinuteHandlerService
from common.services.transcription_handler_service import TranscriptionHandlerService
from common.settings import CLAIM_STALE_AFTER
from tests.utils import get_or_create_user

CUTOFF_NOW = datetime.now(UTC)


async def _current_user_id(session: AsyncSession) -> uuid.UUID:
    return (await get_or_create_user(session, "claim-recovery-test@example.com")).id


async def _cleanup(session: AsyncSession, ids: dict[str, uuid.UUID]) -> None:
    await session.exec(delete(Transcription).where(Transcription.id == ids["transcription_id"]))
    if "minute_version_id" in ids:
        await session.exec(delete(MinuteVersion).where(MinuteVersion.id == ids["minute_version_id"]))
    await session.commit()


@pytest_asyncio.fixture
async def seeded_transcription():
    """A transcription in the given pre-claim state, plus its recording."""
    ids: dict[str, uuid.UUID] = {}

    async with AsyncSession(async_engine, expire_on_commit=False) as session:
        user_id = await _current_user_id(session)
        transcription = Transcription(user_id=user_id, status=JobStatus.AWAITING_START, error=None)
        session.add(transcription)
        await session.flush()
        session.add(
            Recording(
                user_id=user_id, s3_file_key=f"claimtest/{uuid.uuid4().hex}.mp3", transcription_id=transcription.id
            )
        )
        await session.commit()
        ids["transcription_id"] = transcription.id

    yield ids

    async with AsyncSession(async_engine) as session:
        await _cleanup(session, ids)


@pytest_asyncio.fixture
async def seeded_minute_version():
    """A minute version in AWAITING_START state."""
    ids: dict[str, uuid.UUID] = {}

    async with AsyncSession(async_engine, expire_on_commit=False) as session:
        user_id = await _current_user_id(session)
        transcription = Transcription(user_id=user_id, status=JobStatus.FAILED, error=None)
        minute = Minute(template_name="General", transcription_id=transcription.id)
        minute_version = MinuteVersion(minute_id=minute.id, status=JobStatus.AWAITING_START)
        session.add(transcription)
        session.add(minute)
        session.add(minute_version)
        await session.commit()
        ids["transcription_id"] = transcription.id
        ids["minute_id"] = minute.id
        ids["minute_version_id"] = minute_version.id

    yield ids

    async with AsyncSession(async_engine) as session:
        await _cleanup(session, ids)
        await session.exec(delete(Minute).where(Minute.id == ids["minute_id"]))
        await session.commit()


@pytest.mark.asyncio(loop_scope="session")
async def test_transcription_claim_guard_then_stale_reclaim(seeded_transcription):
    transcription_id = seeded_transcription["transcription_id"]

    # fresh claim succeeds; a second delivery of the same message minutes later is a no-op
    assert TranscriptionHandlerService.claim_transcription(transcription_id) is not None
    assert TranscriptionHandlerService.claim_transcription(transcription_id) is None

    # simulate the claimant crashing: the row stays IN_PROGRESS but ages past the window
    stale_updated = CUTOFF_NOW - CLAIM_STALE_AFTER - timedelta(minutes=5)
    async with AsyncSession(async_engine) as session:
        transcription = await session.get(Transcription, transcription_id)
        transcription.updated_datetime = stale_updated
        session.add(transcription)
        await session.commit()

    # redelivery can reclaim the abandoned claim, and the age timer restarts
    assert TranscriptionHandlerService.claim_transcription(transcription_id) is not None

    async with AsyncSession(async_engine) as session:
        transcription = await session.get(Transcription, transcription_id)
        assert transcription.status == JobStatus.IN_PROGRESS
        assert transcription.updated_datetime > stale_updated


@pytest.mark.asyncio(loop_scope="session")
async def test_minute_version_claim_guard_then_stale_reclaim(seeded_minute_version):
    minute_version_id = seeded_minute_version["minute_version_id"]

    assert MinuteHandlerService.claim_minute_version(minute_version_id) is not None
    assert MinuteHandlerService.claim_minute_version(minute_version_id) is None

    stale_updated = CUTOFF_NOW - CLAIM_STALE_AFTER - timedelta(minutes=5)
    async with AsyncSession(async_engine) as session:
        minute_version = await session.get(MinuteVersion, minute_version_id)
        minute_version.updated_datetime = stale_updated
        session.add(minute_version)
        await session.commit()

    assert MinuteHandlerService.claim_minute_version(minute_version_id) is not None

    async with AsyncSession(async_engine) as session:
        minute_version = await session.get(MinuteVersion, minute_version_id)
        assert minute_version.status == JobStatus.IN_PROGRESS
        assert minute_version.updated_datetime > stale_updated


@pytest.mark.asyncio(loop_scope="session")
async def test_stale_claim_token_cannot_write(seeded_transcription):
    """A superseded worker's fenced write must be rejected once another worker
    reclaims the job (its claim token no longer matches the row)."""
    transcription_id = seeded_transcription["transcription_id"]

    stale_token = TranscriptionHandlerService.claim_transcription(transcription_id)
    assert stale_token is not None

    # the claimant is presumed dead and another worker reclaims the job
    async with AsyncSession(async_engine) as session:
        transcription = await session.get(Transcription, transcription_id)
        transcription.updated_datetime = CUTOFF_NOW - CLAIM_STALE_AFTER - timedelta(minutes=5)
        session.add(transcription)
        await session.commit()
    fresh_token = TranscriptionHandlerService.claim_transcription(transcription_id)
    assert fresh_token is not None
    assert fresh_token != stale_token

    # the original (superseded) worker finishing late cannot clobber the new owner
    assert (
        TranscriptionHandlerService.update_transcription(
            transcription_id, status=JobStatus.COMPLETED, claim_token=stale_token
        )
        is False
    )
    # the current owner's write still applies
    assert (
        TranscriptionHandlerService.update_transcription(
            transcription_id, status=JobStatus.COMPLETED, claim_token=fresh_token
        )
        is True
    )
    async with AsyncSession(async_engine) as session:
        transcription = await session.get(Transcription, transcription_id)
        assert transcription.status == JobStatus.COMPLETED


@pytest.mark.asyncio(loop_scope="session")
async def test_job_claim_renewer_rotates_fencing_token(seeded_transcription):
    """Renewal is a short transaction: it rotates the fence token without holding
    a pooled connection across the surrounding job."""
    transcription_id = seeded_transcription["transcription_id"]
    token = TranscriptionHandlerService.claim_transcription(transcription_id)
    assert token is not None

    renewer = JobClaimRenewer(Transcription, transcription_id, token, interval=0.01)
    async with renewer:
        await asyncio.sleep(0.04)

    assert renewer.token != token
    assert (
        TranscriptionHandlerService.update_transcription(
            transcription_id, status=JobStatus.COMPLETED, claim_token=token
        )
        is False
    )
    assert (
        TranscriptionHandlerService.update_transcription(
            transcription_id, status=JobStatus.COMPLETED, claim_token=renewer.token
        )
        is True
    )

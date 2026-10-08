"""Claim-matrix tests for the repository CAS: the claim guard is the idempotency
primitive of the whole worker, so every branch is pinned here against a real Postgres.

These need a reachable Postgres (dev DB / docker compose), like the route tests.
"""

import asyncio
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from sqlalchemy import update
from sqlmodel import col

from common.database.postgres_database import AsyncSessionLocal
from common.database.postgres_models import JobStatus, Minute, MinuteVersion, Transcription
from common.database.repository import (
    ClaimState,
    claim_transcription_for_processing,
    claim_version_for_processing,
    finalize_stale_transcriptions,
    finalize_stale_versions,
    mark_transcription_completed,
    mark_version_completed,
    mark_version_failed,
    refresh_job_leases,
    reset_transcription_for_retry,
    reset_version_for_retry,
)

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


async def _set_claimed_at(model, entity_id, claimed_at: datetime | None) -> None:
    async with AsyncSessionLocal() as session:
        await session.execute(update(model).where(col(model.id) == entity_id).values(claimed_at=claimed_at))
        await session.commit()


@pytest.mark.asyncio(loop_scope="session")
async def test_claim_fresh_row_succeeds_and_stamps_lease():
    transcription, _ = await _make_job()
    try:
        async with AsyncSessionLocal() as session:
            state = await claim_transcription_for_processing(session, transcription.id, STALE_SECONDS)
            await session.commit()
        assert state == ClaimState.CLAIMED
        async with AsyncSessionLocal() as session:
            row = await session.get(Transcription, transcription.id)
            assert row.status == JobStatus.IN_PROGRESS
            assert row.claimed_at is not None
    finally:
        await _delete_transcription(transcription.id)


@pytest.mark.asyncio(loop_scope="session")
async def test_duplicate_message_cannot_reclaim_a_fresh_claim():
    transcription, _ = await _make_job()
    try:
        async with AsyncSessionLocal() as session:
            assert (
                await claim_transcription_for_processing(session, transcription.id, STALE_SECONDS) == ClaimState.CLAIMED
            )
            await session.commit()
            assert (
                await claim_transcription_for_processing(session, transcription.id, STALE_SECONDS)
                == ClaimState.IN_PROGRESS
            )
    finally:
        await _delete_transcription(transcription.id)


@pytest.mark.asyncio(loop_scope="session")
async def test_stale_lease_is_stealable_on_redelivery():
    transcription, _ = await _make_job()
    try:
        async with AsyncSessionLocal() as session:
            assert (
                await claim_transcription_for_processing(session, transcription.id, STALE_SECONDS) == ClaimState.CLAIMED
            )
            await session.commit()
        await _set_claimed_at(Transcription, transcription.id, datetime.now(UTC) - timedelta(seconds=STALE_SECONDS + 1))
        async with AsyncSessionLocal() as session:
            assert (
                await claim_transcription_for_processing(session, transcription.id, STALE_SECONDS) == ClaimState.CLAIMED
            )
            await session.commit()
    finally:
        await _delete_transcription(transcription.id)


@pytest.mark.asyncio(loop_scope="session")
async def test_terminal_rows_are_never_claimable():
    transcription_completed, _ = await _make_job(transcription_status=JobStatus.COMPLETED)
    transcription_failed, version_failed = await _make_job(version_status=JobStatus.FAILED)
    try:
        async with AsyncSessionLocal() as session:
            assert (
                await claim_transcription_for_processing(session, transcription_completed.id, STALE_SECONDS)
                == ClaimState.COMPLETED
            )
            assert await claim_version_for_processing(session, version_failed.id, STALE_SECONDS) == ClaimState.FAILED
    finally:
        await _delete_transcription(transcription_completed.id)
        await _delete_transcription(transcription_failed.id)


@pytest.mark.asyncio(loop_scope="session")
async def test_missing_row_reports_missing():
    async with AsyncSessionLocal() as session:
        assert await claim_transcription_for_processing(session, uuid4(), STALE_SECONDS) == ClaimState.MISSING


@pytest.mark.asyncio(loop_scope="session")
async def test_mark_and_reset_status_transitions():
    transcription, version = await _make_job()
    try:
        async with AsyncSessionLocal() as session:
            await claim_transcription_for_processing(session, transcription.id, STALE_SECONDS)
            await mark_transcription_completed(session, transcription.id, transcript=[], title="T")
            await mark_version_completed(session, version.id, html_content="<p>hi</p>")
            await session.commit()
        async with AsyncSessionLocal() as session:
            t = await session.get(Transcription, transcription.id)
            v = await session.get(MinuteVersion, version.id)
            assert t.status == JobStatus.COMPLETED
            assert t.title == "T"
            assert v.status == JobStatus.COMPLETED
            assert v.html_content == "<p>hi</p>"

        async with AsyncSessionLocal() as session:
            await reset_transcription_for_retry(session, transcription.id)
            await reset_version_for_retry(session, version.id)
            await session.commit()
        async with AsyncSessionLocal() as session:
            t = await session.get(Transcription, transcription.id)
            v = await session.get(MinuteVersion, version.id)
            assert t.status == JobStatus.AWAITING_START
            assert t.claimed_at is None
            assert t.dialogue_entries is None
            assert v.status == JobStatus.AWAITING_START
            assert v.claimed_at is None
            assert v.html_content == ""

        async with AsyncSessionLocal() as session:
            await claim_version_for_processing(session, version.id, STALE_SECONDS)
            await mark_version_failed(session, version.id, "boom")
            await session.commit()
        async with AsyncSessionLocal() as session:
            v = await session.get(MinuteVersion, version.id)
            assert v.status == JobStatus.FAILED
            assert v.error == "boom"
    finally:
        await _delete_transcription(transcription.id)


@pytest.mark.asyncio(loop_scope="session")
async def test_finalize_stale_only_touches_expired_leases():
    stale, _ = await _make_job()
    fresh, _ = await _make_job()
    try:
        async with AsyncSessionLocal() as session:
            await claim_transcription_for_processing(session, stale.id, STALE_SECONDS)
            await claim_transcription_for_processing(session, fresh.id, STALE_SECONDS)
            await session.commit()
        await _set_claimed_at(Transcription, stale.id, datetime.now(UTC) - timedelta(days=2))
        async with AsyncSessionLocal() as session:
            await finalize_stale_transcriptions(session, older_than=timedelta(days=1))
            await finalize_stale_versions(session, older_than=timedelta(days=1))
            await session.commit()
        async with AsyncSessionLocal() as session:
            assert (await session.get(Transcription, stale.id)).status == JobStatus.FAILED
            assert (await session.get(Transcription, fresh.id)).status == JobStatus.IN_PROGRESS
    finally:
        await _delete_transcription(stale.id)
        await _delete_transcription(fresh.id)


@pytest.mark.asyncio(loop_scope="session")
async def test_lease_renewal_prevents_steal_of_a_legitimately_long_job():
    """The consumer heartbeat renews claimed_at every interval; while it does, no
    duplicate message may steal the claim - however long the job runs."""
    transcription, version = await _make_job()
    try:
        async with AsyncSessionLocal() as session:
            state = await claim_transcription_for_processing(session, transcription.id, STALE_SECONDS)
            assert state == ClaimState.CLAIMED
            await session.commit()
        # several heartbeat ticks, as a long job would produce
        for _ in range(3):
            await asyncio.sleep(0.05)
            async with AsyncSessionLocal() as session:
                await refresh_job_leases(session, version.id)
                await session.commit()
            async with AsyncSessionLocal() as session:
                state = await claim_transcription_for_processing(session, transcription.id, STALE_SECONDS)
                assert state == ClaimState.IN_PROGRESS
        # once renewal stops and the lease expires, the claim is stealable again
        await _set_claimed_at(Transcription, transcription.id, datetime.now(UTC) - timedelta(seconds=STALE_SECONDS + 1))
        async with AsyncSessionLocal() as session:
            state = await claim_transcription_for_processing(session, transcription.id, STALE_SECONDS)
            assert state == ClaimState.CLAIMED
            await session.commit()
    finally:
        await _delete_transcription(transcription.id)


@pytest.mark.asyncio(loop_scope="session")
async def test_refresh_job_leases_only_touches_in_progress_rows():
    transcription, version = await _make_job()
    try:
        async with AsyncSessionLocal() as session:
            await claim_transcription_for_processing(session, transcription.id, STALE_SECONDS)
            await session.commit()
        old = datetime.now(UTC) - timedelta(seconds=STALE_SECONDS * 2)
        await _set_claimed_at(Transcription, transcription.id, old)
        await _set_claimed_at(MinuteVersion, version.id, old)  # version is AWAITING_START: must stay untouched
        async with AsyncSessionLocal() as session:
            await refresh_job_leases(session, version.id)
            await session.commit()
        async with AsyncSessionLocal() as session:
            t = await session.get(Transcription, transcription.id)
            v = await session.get(MinuteVersion, version.id)
            assert t.claimed_at is not None  # renewed: status was IN_PROGRESS
            assert t.claimed_at > old
            assert v.claimed_at == old  # untouched: status was AWAITING_START
    finally:
        await _delete_transcription(transcription.id)

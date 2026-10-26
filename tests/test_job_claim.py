"""claim_job moves AWAITING_START -> IN_PROGRESS exactly once."""

import pytest
from sqlmodel import delete
from sqlmodel.ext.asyncio.session import AsyncSession

from common.database.postgres_database import async_engine
from common.database.postgres_models import JobStatus, Transcription
from common.services.job_claim import claim_job
from tests.utils import get_or_create_user


@pytest.mark.asyncio(loop_scope="session")
async def test_claim_job_is_a_one_way_awaiting_start_transition():
    async with AsyncSession(async_engine, expire_on_commit=False) as session:
        user = await get_or_create_user(session, "job-claim-test@example.com")
        transcription = Transcription(user_id=user.id, status=JobStatus.AWAITING_START)
        session.add(transcription)
        await session.commit()
        transcription_id = transcription.id

    try:
        assert claim_job(Transcription, transcription_id) is True
        assert claim_job(Transcription, transcription_id) is False  # already IN_PROGRESS
        async with AsyncSession(async_engine) as session:
            assert (await session.get(Transcription, transcription_id)).status == JobStatus.IN_PROGRESS
    finally:
        async with AsyncSession(async_engine) as session:
            await session.exec(delete(Transcription).where(Transcription.id == transcription_id))
            await session.commit()

"""The generated title must never overwrite a title the user set after completion."""

import pytest
from sqlmodel import col, delete
from sqlmodel.ext.asyncio.session import AsyncSession

from common.database.postgres_database import async_engine
from common.database.postgres_models import JobStatus, Transcription
from common.workflows.activities import _shared
from tests.utils import get_or_create_user


@pytest.mark.asyncio(loop_scope="session")
async def test_set_title_if_empty_never_overwrites_a_user_title():
    async with AsyncSession(async_engine, expire_on_commit=False) as session:
        user = await get_or_create_user(session, "title-guard-test@example.com")
        renamed = Transcription(user_id=user.id, status=JobStatus.COMPLETED, title="User renamed")
        untitled = Transcription(user_id=user.id, status=JobStatus.COMPLETED, title="")
        session.add(renamed)
        session.add(untitled)
        await session.commit()
        ids = (renamed.id, untitled.id)

    try:
        assert _shared.set_title_if_empty(ids[0], "Generated") is False
        assert _shared.set_title_if_empty(ids[1], "Generated") is True

        async with AsyncSession(async_engine) as session:
            assert (await session.get(Transcription, ids[0])).title == "User renamed"
            assert (await session.get(Transcription, ids[1])).title == "Generated"
    finally:
        async with AsyncSession(async_engine) as session:
            await session.exec(delete(Transcription).where(col(Transcription.id).in_(ids)))
            await session.commit()

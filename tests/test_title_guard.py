"""Generated metadata fills only missing values on in-progress transcriptions."""

from datetime import timedelta

import pytest
from sqlmodel import col, delete
from sqlmodel.ext.asyncio.session import AsyncSession

from common.database.postgres_database import async_engine
from common.database.postgres_models import JobStatus, Transcription
from common.workflows.activities import _shared


@pytest.mark.asyncio(loop_scope="session")
async def test_generated_metadata_preserves_existing_values_and_completed_rows():
    async with AsyncSession(async_engine, expire_on_commit=False) as session:
        renamed = Transcription(status=JobStatus.IN_PROGRESS, title="User renamed")
        untitled = Transcription(status=JobStatus.IN_PROGRESS, title="")
        cleared = Transcription(status=JobStatus.IN_PROGRESS, search_keywords=[])
        completed = Transcription(status=JobStatus.COMPLETED, title="")
        rows = (renamed, untitled, cleared, completed)
        session.add_all(rows)
        await session.commit()
        ids = [row.id for row in rows]

    try:
        for row in (renamed, untitled, cleared):
            assert _shared.set_generated_title_and_keywords(row, "Generated", ["FOI"])
        assert not _shared.set_generated_title_and_keywords(untitled, "Different title", ["Different keyword"])
        assert not _shared.set_generated_title_and_keywords(completed, "Generated", ["FOI"])

        async with AsyncSession(async_engine) as session:
            expected = [("User renamed", ["FOI"], True), ("Generated", ["FOI"], True), ("Generated", [], False)]
            for tid, metadata in zip(ids[:3], expected, strict=True):
                row = await session.get(Transcription, tid)
                assert (row.title, row.search_keywords, row.search_keywords_generated) == metadata
            retried = await session.get(Transcription, completed.id)
            retried.status = JobStatus.IN_PROGRESS
            retried.created_datetime += timedelta(seconds=1)
            await session.commit()
        assert not _shared.set_generated_title_and_keywords(completed, "Stale title", ["old topic"])
    finally:
        async with AsyncSession(async_engine) as session:
            await session.exec(delete(Transcription).where(col(Transcription.id).in_(ids)))
            await session.commit()

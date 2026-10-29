import pytest_asyncio
from sqlmodel import delete
from sqlmodel.ext.asyncio.session import AsyncSession

from common.database.postgres_database import async_engine
from common.database.postgres_models import JobStatus, Minute, MinuteVersion, Transcription
from tests.utils import get_or_create_user


@pytest_asyncio.fixture
async def minute_version_setup():
    """A completed transcript and unfinished minute; deleting the transcript cascades to its minutes."""
    async with AsyncSession(async_engine, expire_on_commit=False) as session:
        user = await get_or_create_user(session, "minute-recovery-test@example.com")
        transcription = Transcription(
            user_id=user.id,
            status=JobStatus.COMPLETED,
            dialogue_entries=[{"speaker": "A", "text": "hello", "start_time": 0.0, "end_time": 1.0}],
        )
        minute = Minute(transcription_id=transcription.id)
        version = MinuteVersion(minute_id=minute.id, ai_edit_instructions="Shorten it")
        session.add_all([transcription, minute, version])
        await session.commit()
        ids = {"transcription_id": transcription.id, "minute_id": minute.id, "minute_version_id": version.id}
    yield ids
    async with AsyncSession(async_engine) as session:
        await session.exec(delete(Transcription).where(Transcription.id == ids["transcription_id"]))
        await session.commit()

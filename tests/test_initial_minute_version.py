"""The initial generation must target the INITIAL_GENERATION version, not a later AI edit."""

import pytest
from sqlmodel import delete
from sqlmodel.ext.asyncio.session import AsyncSession

from common.database.postgres_database import async_engine
from common.database.postgres_models import ContentSource, JobStatus, Minute, MinuteVersion, Transcription
from common.services.minute_handler_service import MinuteHandlerService
from tests.utils import get_or_create_user


@pytest.mark.asyncio(loop_scope="session")
async def test_initial_minute_version_is_found_alongside_edits():
    async with AsyncSession(async_engine, expire_on_commit=False) as session:
        user = await get_or_create_user(session, "initial-version-test@example.com")
        transcription = Transcription(user_id=user.id, status=JobStatus.COMPLETED)
        session.add(transcription)
        await session.flush()
        minute = Minute(template_name="General", transcription_id=transcription.id)
        session.add(minute)
        await session.flush()
        initial = MinuteVersion(minute_id=minute.id, status=JobStatus.COMPLETED)
        edit = MinuteVersion(minute_id=minute.id, status=JobStatus.COMPLETED, content_source=ContentSource.AI_EDIT)
        session.add(initial)
        session.add(edit)
        await session.commit()
        transcription_id, minute_id, initial_id = transcription.id, minute.id, initial.id

    try:
        found = await MinuteHandlerService.get_initial_minute_version_for_minute_id(minute_id)
        assert found.id == initial_id
    finally:
        async with AsyncSession(async_engine) as session:
            await session.exec(delete(MinuteVersion).where(MinuteVersion.minute_id == minute_id))
            await session.exec(delete(Minute).where(Minute.id == minute_id))
            await session.exec(delete(Transcription).where(Transcription.id == transcription_id))
            await session.commit()

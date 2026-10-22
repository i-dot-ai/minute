"""Behaviour test for delete_orphan_records, covering the FOR UPDATE selection
added for minute_954b vuln-0002 (cleanup must not delete an attached recording).
"""

import uuid

import pytest
import pytest_asyncio
from sqlmodel import col, delete
from sqlmodel.ext.asyncio.session import AsyncSession

from backend.cleanup_job import delete_orphan_records
from common.database.postgres_database import async_engine
from common.database.postgres_models import Recording, Transcription
from tests.utils import get_or_create_user


async def _user_id(session: AsyncSession) -> uuid.UUID:
    return (await get_or_create_user(session, "cleanup-test@example.com")).id


@pytest_asyncio.fixture
async def recordings() -> dict[str, uuid.UUID]:
    ids: dict[str, uuid.UUID] = {}
    async with AsyncSession(async_engine, expire_on_commit=False) as session:
        user_id = await _user_id(session)
        transcription = Transcription(user_id=user_id)
        session.add(transcription)
        await session.flush()
        orphan = Recording(user_id=user_id, s3_file_key=f"cleanuptest/{uuid.uuid4().hex}.mp3")
        attached = Recording(
            user_id=user_id, s3_file_key=f"cleanuptest/{uuid.uuid4().hex}.mp3", transcription_id=transcription.id
        )
        session.add(orphan)
        session.add(attached)
        await session.commit()
        ids.update(orphan_id=orphan.id, attached_id=attached.id, transcription_id=transcription.id)

    yield ids

    async with AsyncSession(async_engine) as session:
        await session.exec(delete(Recording).where(col(Recording.id).in_([ids["orphan_id"], ids["attached_id"]])))
        await session.exec(delete(Transcription).where(Transcription.id == ids["transcription_id"]))
        await session.commit()


@pytest.mark.asyncio(loop_scope="session")
async def test_delete_orphan_records_keeps_attached_ones(recordings, monkeypatch):
    deleted_objects: list[str] = []

    async def _exists(_storage, _key: str) -> bool:
        return True

    async def _delete(_storage, key: str) -> None:
        deleted_objects.append(key)

    monkeypatch.setattr("backend.cleanup_job.exists", _exists)
    monkeypatch.setattr("backend.cleanup_job.delete", _delete)

    await delete_orphan_records()

    async with AsyncSession(async_engine) as session:
        assert await session.get(Recording, recordings["orphan_id"]) is None
        attached = await session.get(Recording, recordings["attached_id"])
        assert attached is not None
        assert attached.transcription_id == recordings["transcription_id"]

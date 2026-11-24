"""Orphan cleanup preserves attached recordings and recovers from deletion failures."""

import uuid
from unittest.mock import AsyncMock

import pytest
import pytest_asyncio
from sqlalchemy.exc import OperationalError
from sqlmodel import col, delete
from sqlmodel.ext.asyncio.session import AsyncSession
from temporalio.testing import ActivityEnvironment

from common.database.postgres_database import async_engine
from common.database.postgres_models import Recording, Transcription
from common.services.storage_services.local import local
from common.workflows.activities import cleanup
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

    async def _delete(key: str) -> None:
        deleted_objects.append(key)

    monkeypatch.setattr(cleanup.storage_service, "delete", _delete)

    await ActivityEnvironment().run(cleanup.delete_orphan_records)
    await ActivityEnvironment().run(cleanup.delete_orphan_records)
    assert len(deleted_objects) == 1

    async with AsyncSession(async_engine) as session:
        assert await session.get(Recording, recordings["orphan_id"]) is None
        attached = await session.get(Recording, recordings["attached_id"])
        assert attached is not None
        assert attached.transcription_id == recordings["transcription_id"]


@pytest.mark.asyncio(loop_scope="session")
async def test_storage_failure_keeps_recording_for_retry(recordings, monkeypatch):
    async with AsyncSession(async_engine, expire_on_commit=False) as session:
        orphan = await session.get(Recording, recordings["orphan_id"])
        successful = Recording(user_id=orphan.user_id, s3_file_key=f"cleanuptest/{uuid.uuid4().hex}.mp3")
        session.add(successful)
        await session.commit()

    async def _delete(key: str) -> None:
        if key == orphan.s3_file_key:
            msg = "storage unavailable"
            raise ConnectionError(msg)

    delete_object = AsyncMock(side_effect=_delete)
    monkeypatch.setattr(cleanup.storage_service, "delete", delete_object)

    with pytest.raises(ConnectionError, match="storage unavailable"):
        await ActivityEnvironment().run(cleanup.delete_orphan_records)
    async with AsyncSession(async_engine) as session:
        assert await session.get(Recording, recordings["orphan_id"]) is not None
        assert await session.get(Recording, successful.id) is None

    delete_object.side_effect = None
    await ActivityEnvironment().run(cleanup.delete_orphan_records)
    async with AsyncSession(async_engine) as session:
        assert await session.get(Recording, recordings["orphan_id"]) is None


@pytest.mark.asyncio(loop_scope="session")
async def test_retry_after_file_deleted_but_database_commit_failed(recordings, monkeypatch, tmp_path):
    async with AsyncSession(async_engine) as session:
        orphan = await session.get(Recording, recordings["orphan_id"])
        path = tmp_path / orphan.s3_file_key
    path.parent.mkdir(parents=True)
    path.write_bytes(b"audio")
    monkeypatch.setattr(local.settings, "LOCAL_STORAGE_PATH", str(tmp_path))
    monkeypatch.setattr(cleanup, "storage_service", local.LocalStorageService)
    error = OperationalError("COMMIT", None, ConnectionError("database unavailable"))

    async def fail_commit(session):
        await session.flush()
        raise error

    with monkeypatch.context() as patch:
        patch.setattr(AsyncSession, "commit", fail_commit)
        with pytest.raises(OperationalError, match="database unavailable"):
            await ActivityEnvironment().run(cleanup.delete_orphan_records)

    assert not path.exists()
    async with AsyncSession(async_engine) as session:
        assert await session.get(Recording, recordings["orphan_id"]) is not None

    await ActivityEnvironment().run(cleanup.delete_orphan_records)
    async with AsyncSession(async_engine) as session:
        assert await session.get(Recording, recordings["orphan_id"]) is None

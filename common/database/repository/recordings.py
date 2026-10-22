from uuid import UUID

from sqlmodel import col, select
from sqlmodel.ext.asyncio.session import AsyncSession

from common.database.postgres_models import Recording


async def add_recording(
    session: AsyncSession, recording_id: UUID, s3_file_key: str, user_id: UUID, transcription_id: UUID | None
) -> Recording:
    recording = Recording(id=recording_id, s3_file_key=s3_file_key, user_id=user_id, transcription_id=transcription_id)
    session.add(recording)
    return recording


async def find_orphan_recordings(session: AsyncSession) -> list[Recording]:
    """Recordings no transcription points at, locked so a concurrent POST /transcriptions can't attach one."""
    statement = select(Recording).where(col(Recording.transcription_id).is_(None)).with_for_update()
    return list((await session.exec(statement)).all())

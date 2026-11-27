from fastapi import HTTPException
from sqlmodel.ext.asyncio.session import AsyncSession

from backend.utils import temporal
from common.database.postgres_models import (
    JobStatus,
    MinuteVersion,
    Transcription,
)


async def enqueue_transcription(
    session: AsyncSession, transcription: Transcription, minute_version: MinuteVersion
) -> None:
    """Commit before starting the workflow so the worker can always see the job row."""
    await session.commit()
    try:
        await temporal.start_transcription_workflow(
            transcription.id,
            minute_version.minute_id,
            user_id=transcription.user_id,
            minute_version_id=minute_version.id,
        )
    except Exception as exc:
        transcription.status = JobStatus.FAILED
        transcription.error = "Failed to enqueue transcription"
        await session.commit()
        raise HTTPException(status_code=503, detail="Failed to enqueue transcription") from exc

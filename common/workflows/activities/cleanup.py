"""Daily retention, orphaned-audio and stalled-record cleanup activities."""

import logging
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from sqlmodel import and_, col, func, null, select, update
from sqlmodel.ext.asyncio.session import AsyncSession
from temporalio import activity

from common.database.postgres_database import async_engine
from common.database.postgres_models import JobStatus, MinuteVersion, Recording, Transcription, User
from common.services.storage_services import get_storage_service
from common.settings import get_settings

logger = logging.getLogger(__name__)

settings = get_settings()

storage_service = get_storage_service(settings.STORAGE_SERVICE_NAME)


@activity.defn
async def cleanup_failed_records() -> None:
    """Mark records still in progress after 24 hours as failed."""
    logger.info("Starting stalled object cleanup process")
    async with AsyncSession(async_engine) as session:
        for object_type in [MinuteVersion, Transcription]:
            cutoff_date = datetime.now(tz=ZoneInfo("Europe/London")) - timedelta(days=1)
            update_stmt = (
                update(object_type)
                .where(and_(object_type.created_datetime < cutoff_date, object_type.status == JobStatus.IN_PROGRESS))
                .values(status=JobStatus.FAILED, error="Unknown error. Job finalised by cleanup process")
            )
            result = await session.exec(update_stmt)
            await session.commit()
            logger.info(
                f"updated {result.rowcount} old {object_type.__qualname__} that were not successfully processed"  # noqa: G004
            )

    logger.info("Stalled record cleanup process completed")


@activity.defn
async def cleanup_old_records() -> None:
    """Delete records based on each user's retention period setting."""
    logger.info("Starting data retention cleanup process")
    async with AsyncSession(async_engine) as session:
        statement = (
            select(Transcription)
            .join(User, User.id == Transcription.user_id)
            .where(
                col(User.data_retention_days).is_not(null()),
                Transcription.created_datetime < func.now() - User.data_retention_days * timedelta(days=1),
            )
        )
        transcriptions = (await session.exec(statement)).all()
        logger.info("Deleting %d transcriptions.", len(transcriptions))
        for transcription in transcriptions:
            await session.delete(transcription)
        await session.commit()


@activity.defn
async def delete_orphan_records() -> None:
    logger.info("Starting recording clean up")
    failure: Exception | None = None
    activity.heartbeat()
    async with AsyncSession(async_engine) as session:
        orphan_recording_query = select(Recording).where(col(Recording.transcription_id).is_(None)).with_for_update()
        recordings = (await session.exec(orphan_recording_query)).all()
        logger.info("Found %d Recordings with no Transcription.", len(recordings))
        for recording in recordings:
            activity.heartbeat()
            try:
                # Both storage services allow repeated deletion, including an already-missing object.
                await storage_service.delete(recording.s3_file_key)
            except Exception as e:
                logger.exception("Error deleting recording %s; keeping its database row", recording.id)
                failure = e
            else:
                await session.delete(recording)
        await session.commit()

    if failure is not None:
        raise failure  # Successful deletions are committed; Temporal retries the remaining rows.
    logger.info("Data retention cleanup process completed")

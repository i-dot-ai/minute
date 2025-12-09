import logging
from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlmodel import and_, col, func, null, select, update
from sqlmodel.ext.asyncio.session import AsyncSession

from common.database.postgres_database import async_engine
from common.database.postgres_models import JobStatus, MinuteVersion, Recording, Transcription, User
from common.services.storage_services import get_storage_service
from common.settings import get_settings

logger = logging.getLogger()
logger.setLevel(logging.INFO)

settings = get_settings()

storage_service = get_storage_service(settings.STORAGE_SERVICE_NAME)


async def cleanup_failed_records():
    """clear records based on each user's retention period setting."""
    logger.info("Starting stalled object cleanup process")
    async with AsyncSession(async_engine) as session:
        for object_type in [MinuteVersion, Transcription]:
            # delete after 24 hrs if not successful
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


async def cleanup_old_records():
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


async def delete_orphan_records():
    logger.info("Starting recording clean up")
    async with AsyncSession(async_engine) as session:
        orphan_recording_query = select(Recording).where(col(Recording.transcription_id).is_(None))
        recordings = (await session.exec(orphan_recording_query)).all()
        logger.info("Found %d Recordings with no Transcription.", len(recordings))
        for recording in recordings:
            try:
                exists = await storage_service.check_object_exists(recording.s3_file_key)
                if exists:
                    await storage_service.delete(recording.s3_file_key)
                await storage_service.delete(recording.s3_file_key)
            except Exception as e:  # noqa: BLE001
                msg = f"Error deleting recording {recording.id}. Will keep record in database: {e}"
                logger.error(msg)
            else:
                await session.delete(recording)
        await session.commit()

    logger.info("Data retention cleanup process completed")


async def cleanup_jobs():
    await cleanup_old_records()
    await delete_orphan_records()
    await cleanup_failed_records()


async def init_cleanup_scheduler():
    """Initialize the scheduler to run cleanup daily."""
    next_run_time = datetime.now(tz=UTC).replace(hour=23, minute=0, second=0, microsecond=0)
    scheduler = AsyncIOScheduler()
    scheduler.add_job(cleanup_jobs, "interval", days=1, next_run_time=next_run_time)
    scheduler.start()
    logger.info("cleanup scheduler initialized")

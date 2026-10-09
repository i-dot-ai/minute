import logging
from datetime import UTC, datetime, timedelta

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlmodel import col, func, null, select
from sqlmodel.ext.asyncio.session import AsyncSession

from common.database.postgres_database import async_engine
from common.database.postgres_models import Recording, Transcription, User
from common.database.repository import finalize_stale_transcriptions, finalize_stale_versions
from common.services.storage import S3
from common.settings import get_settings

logger = logging.getLogger()
logger.setLevel(logging.INFO)

settings = get_settings()

storage_service = S3()


async def cleanup_failed_records():
    """Finalise jobs stuck IN_PROGRESS past the lease horizon (worker died and was never re-claimed)."""
    logger.info("Starting stalled object cleanup process")
    async with AsyncSession(async_engine) as session:
        for finalize, label in [
            (finalize_stale_versions, "MinuteVersion"),
            (finalize_stale_transcriptions, "Transcription"),
        ]:
            # delete after 24 hrs if not successful
            result = await finalize(session, older_than=timedelta(days=1))
            await session.commit()
            logger.info(f"updated {result} old {label} that were not successfully processed")  # noqa: G004

    logger.info("Stalled record cleanup process completed")


async def cleanup_old_records():
    """Delete records based on each user's retention period setting."""
    logger.info("Starting data retention cleanup process")
    async with AsyncSession(async_engine) as session:
        statement = (
            select(Transcription)
            .join(User, col(User.id) == col(Transcription.user_id))
            .where(
                col(User.data_retention_days).is_not(null()),
                col(Transcription.created_datetime) < func.now() - col(User.data_retention_days) * timedelta(days=1),
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

import logging
from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from common.database.postgres_database import AsyncSessionLocal
from common.database.postgres_models import MinuteVersion, Transcription
from common.database.repository import (
    finalize_stale_in_progress,
    find_expired_transcriptions,
    find_orphan_recordings,
)
from common.services.storage.s3 import client, delete, exists
from common.settings import get_settings

logger = logging.getLogger()
logger.setLevel(logging.INFO)

settings = get_settings()


async def cleanup_failed_records():
    """Fail jobs stuck IN_PROGRESS for over a day so users can retry them."""
    logger.info("Starting stalled object cleanup process")
    cutoff_date = datetime.now(tz=ZoneInfo("Europe/London")) - timedelta(days=1)
    async with AsyncSessionLocal() as session:
        for object_type in [MinuteVersion, Transcription]:
            count = await finalize_stale_in_progress(
                session, object_type, cutoff_date, "Unknown error. Job finalised by cleanup process"
            )
            await session.commit()
            logger.info("updated %d old %s that were not successfully processed", count, object_type.__qualname__)

    logger.info("Stalled record cleanup process completed")


async def cleanup_old_records():
    """Delete records based on each user's retention period setting."""
    logger.info("Starting data retention cleanup process")
    async with AsyncSessionLocal() as session:
        transcriptions = await find_expired_transcriptions(session)
        logger.info("Deleting %d transcriptions.", len(transcriptions))
        for transcription in transcriptions:
            await session.delete(transcription)
        await session.commit()


async def delete_orphan_records():
    logger.info("Starting recording clean up")
    async with AsyncSessionLocal() as session, client() as s3:
        recordings = await find_orphan_recordings(session)
        logger.info("Found %d Recordings with no Transcription.", len(recordings))
        for recording in recordings:
            try:
                if await exists(s3, recording.s3_file_key):
                    await delete(s3, recording.s3_file_key)
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

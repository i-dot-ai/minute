import asyncio
import logging
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from apscheduler.schedulers.background import BackgroundScheduler
from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import create_async_engine
from sqlmodel import Session, and_, col, create_engine, delete, or_, select, update

from common.database.postgres_models import JobStatus, MinuteVersion, Recording, Transcription, User
from common.services.storage_services import get_storage_service
from common.settings import get_settings

# Load environment variables from .env file
load_dotenv()

logger = logging.getLogger(__name__)


# Only create the settings object once

settings = get_settings()

storage_service = get_storage_service(settings.STORAGE_SERVICE_NAME)

# Get database connection details from environment variables
DB_USER = settings.POSTGRES_USER
DB_PASSWORD = settings.POSTGRES_PASSWORD
DB_HOST = settings.POSTGRES_HOST
DB_PORT = settings.POSTGRES_PORT
DB_NAME = settings.POSTGRES_DB

# Use psycopg2 for synchronous operations
SYNC_DATABASE_URL = f"postgresql+psycopg2://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
# Use asyncpg for asynchronous operations
ASYNC_DATABASE_URL = f"postgresql+asyncpg://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

engine = create_engine(SYNC_DATABASE_URL, pool_size=20, max_overflow=30, pool_timeout=60, pool_pre_ping=True)

async_engine = create_async_engine(
    ASYNC_DATABASE_URL, pool_size=20, max_overflow=30, pool_timeout=60, pool_pre_ping=True
)


def SessionLocal() -> Session:  # noqa: N802
    return Session(engine)


def cleanup_failed_records():
    """clear records based on each user's retention period setting."""
    logger.info("Starting stalled object cleanup process")
    with Session(engine) as session:
        for object_type in [MinuteVersion, Transcription]:
            # delete after 24 hrs if not successful
            cutoff_date = datetime.now(tz=ZoneInfo("Europe/London")) - timedelta(days=1)
            update_stmt = (
                update(object_type)
                .where(
                    and_(
                        object_type.created_datetime < cutoff_date,
                        or_(
                            object_type.status == JobStatus.IN_PROGRESS, object_type.status == JobStatus.AWAITING_START
                        ),
                    )
                )
                .values(status=JobStatus.FAILED, error="Unknown error. Job finalised by cleanup process")
            )
            result = session.exec(update_stmt)
            session.commit()
            logger.info(
                f"updated {result.rowcount} old {object_type.__qualname__} that were not successfully processed"  # noqa: G004
            )

    logger.info("Stalled record cleanup process completed")


def cleanup_old_records():
    """Delete records based on each user's retention period setting."""
    logger.info("Starting data retention cleanup process")
    with Session(engine) as session:
        deletion_tasks = []
        # Get all users who have a retention period set
        users = session.exec(select(User)).all()
        logger.info(
            f"Found {len(users)} users"  # noqa: G004
        )

        for user in users:
            # delete after 24 hrs always for cabinet and dsit
            cutoff_date = None
            parts = user.email.split("@")
            # assume the email is well formed. If not use the whole thing
            domain = parts[1].lower() if len(parts) == 2 else user.email.lower()  # noqa: PLR2004
            if len(parts) == 2 and ("cabinetoffice" in domain or "dsit" in domain):  # noqa: PLR2004
                cutoff_date = datetime.now(tz=ZoneInfo("Europe/London")) - timedelta(days=1)
            elif user.data_retention_days:
                cutoff_date = datetime.now(tz=ZoneInfo("Europe/London")) - timedelta(days=user.data_retention_days)
            if cutoff_date:
                # Delete old transcriptions for this user
                delete_stmt = delete(Transcription).where(
                    Transcription.user_id == user.id,
                    Transcription.created_datetime < cutoff_date,
                )
                result = session.exec(delete_stmt)
                session.commit()
                logger.info(
                    f"Deleted {result.rowcount} old transcriptions for user {user.id} (retention: {user.data_retention_days} days)"  # noqa: G004, E501
                )

        recordings = session.exec(select(Recording).where(col(Recording.transcription_id).is_(None))).all()
        for recording in recordings:
            try:
                deletion_tasks.append(asyncio.create_task(storage_service.delete(recording.s3_file_key)))
            finally:
                session.delete(recording)
        session.commit()
    logger.info("Data retention cleanup process completed")


def init_cleanup_scheduler():
    """Initialize the scheduler to run cleanup daily."""
    # Run cleanup immediately on startup
    cleanup_old_records()
    cleanup_failed_records()
    scheduler = BackgroundScheduler()
    # Schedule daily cleanup
    scheduler.add_job(cleanup_old_records, "interval", days=1)
    scheduler.add_job(cleanup_failed_records, "interval", days=1)
    scheduler.start()
    logger.info("cleanup scheduler initialized")

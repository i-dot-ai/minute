from uuid import UUID

from sqlalchemy import update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.exc import SQLAlchemyError
from sqlmodel import col
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from common.database.postgres_database import SessionLocal
from common.database.postgres_models import JobStatus, MinuteVersion, Recording, Transcription
from common.settings import get_structured_logger

slogger = get_structured_logger()


@retry(
    retry=retry_if_exception_type(SQLAlchemyError),
    stop=stop_after_attempt(4),
    wait=wait_exponential(multiplier=1, min=1, max=4),
    reraise=True,
)
def add_recording(
    user_id: UUID,
    transcription_id: UUID,
    recording_id: UUID,
    s3_file_key: str,
) -> None:
    with SessionLocal() as session:
        session.exec(
            insert(Recording)
            .values(
                id=recording_id,
                s3_file_key=s3_file_key,
                user_id=user_id,
                transcription_id=transcription_id,
            )
            .on_conflict_do_nothing(index_elements=["id"])
        )
        session.commit()


@retry(
    retry=retry_if_exception_type(SQLAlchemyError),
    stop=stop_after_attempt(4),
    wait=wait_exponential(multiplier=1, min=1, max=4),
    reraise=True,
)
def mark_transcription_failed(
    transcription_id: UUID,
    minute_id: UUID,
    run_id: UUID | None,
    error: str,
) -> bool:
    with SessionLocal() as session:
        result = session.exec(
            update(Transcription)
            .where(
                col(Transcription.id) == transcription_id,
                col(Transcription.run_id) == run_id,
                col(Transcription.status) == JobStatus.AWAITING_START,
            )
            .values(status=JobStatus.FAILED, error=error)
        )
        if result.rowcount != 1:
            return False
        session.exec(
            update(MinuteVersion)
            .where(
                col(MinuteVersion.minute_id) == minute_id,
                col(MinuteVersion.status) == JobStatus.AWAITING_START,
            )
            .values(status=JobStatus.FAILED, error=error)
        )
        session.commit()
        return True

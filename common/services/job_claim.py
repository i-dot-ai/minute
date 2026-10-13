"""Atomic job claiming shared by the transcription and minute worker paths."""

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import and_, or_, update
from sqlmodel import SQLModel

from common.database.postgres_database import SessionLocal
from common.database.postgres_models import JobStatus
from common.settings import CLAIM_STALE_AFTER


def claim_job(model: type[SQLModel], job_id: UUID) -> bool:
    """Move an AWAITING_START job to IN_PROGRESS, atomically.

    Also reclaims an IN_PROGRESS job whose claim is older than CLAIM_STALE_AFTER:
    that can only happen if the claiming worker died (the heartbeat kills it long
    before), so it cannot race a live job. Returns True when this caller owns it.
    """
    stale_before = datetime.now(UTC) - CLAIM_STALE_AFTER
    with SessionLocal() as session:
        result = session.exec(
            update(model)
            .where(
                model.id == job_id,
                or_(
                    model.status == JobStatus.AWAITING_START,
                    and_(model.status == JobStatus.IN_PROGRESS, model.updated_datetime < stale_before),
                ),
            )
            .values(status=JobStatus.IN_PROGRESS)
        )
        session.commit()
        return result.rowcount == 1

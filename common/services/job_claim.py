"""Atomically start a job: AWAITING_START -> IN_PROGRESS.

Temporal owns retries and runs one workflow per job, so there is no ownership token, staleness or
renewal any more: the status guard on each write is all that is needed.
"""

from uuid import UUID

from sqlalchemy import update
from sqlmodel import SQLModel

from common.database.postgres_database import SessionLocal
from common.database.postgres_models import JobStatus


def claim_job(model: type[SQLModel], job_id: UUID) -> bool:
    """Move an AWAITING_START job to IN_PROGRESS. False if it was already claimed or is terminal."""
    with SessionLocal() as session:
        result = session.exec(
            update(model)
            .where(model.id == job_id, model.status == JobStatus.AWAITING_START)
            .values(status=JobStatus.IN_PROGRESS)
        )
        session.commit()
        return result.rowcount == 1  # pyright: ignore[reportAttributeAccessIssue]

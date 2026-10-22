"""Atomic, renewable job ownership without extra schema."""

import asyncio
import logging
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import and_, or_, update
from sqlmodel import SQLModel

from common.database.postgres_database import SessionLocal
from common.settings import CLAIM_STALE_AFTER
from common.types import JobStatus

logger = logging.getLogger(__name__)
CLAIM_RENEW_INTERVAL_SECONDS = 60


def claim_job(model: type[SQLModel], job_id: UUID, *, include_awaiting: bool = True) -> datetime | None:
    """Claim awaiting or abandoned work and return a completion fencing token.

    include_awaiting=False only takes over abandoned IN_PROGRESS work, so a stale
    async poll message can never hijack a fresh (e.g. retried) AWAITING_START job.
    """
    stale_before = datetime.now(UTC) - CLAIM_STALE_AFTER
    claimable = [and_(model.status == JobStatus.IN_PROGRESS, model.updated_datetime < stale_before)]
    if include_awaiting:
        claimable.append(model.status == JobStatus.AWAITING_START)
    with SessionLocal() as session:
        result = session.exec(
            update(model).where(model.id == job_id, or_(*claimable)).values(status=JobStatus.IN_PROGRESS)
        )
        session.commit()
        if result.rowcount != 1:
            return None
        claimed = session.get(model, job_id)
        return claimed.updated_datetime if claimed else None


def refresh_job(model: type[SQLModel], job_id: UUID, token: datetime) -> datetime | None:
    """Refresh an async poll chain only when its previous fencing token still owns it."""
    with SessionLocal() as session:
        result = session.exec(
            update(model)
            .where(model.id == job_id, model.status == JobStatus.IN_PROGRESS, model.updated_datetime == token)
            .values(status=JobStatus.IN_PROGRESS)
        )
        session.commit()
        if result.rowcount != 1:
            return None
        job = session.get(model, job_id)
        return job.updated_datetime if job else None


class JobClaimRenewer:
    """Refresh a claim without holding a database connection during the job."""

    def __init__(
        self,
        model: type[SQLModel],
        job_id: UUID,
        token: datetime,
        interval: float = CLAIM_RENEW_INTERVAL_SECONDS,
    ):
        self.model = model
        self.job_id = job_id
        self.token = token
        self.interval = interval
        self._task: asyncio.Task | None = None
        self._stop = asyncio.Event()

    async def __aenter__(self) -> "JobClaimRenewer":
        self._stop.clear()
        self._task = asyncio.create_task(self._run())
        return self

    async def __aexit__(self, *_exc: object) -> None:
        if self._task is None:
            return
        self._stop.set()
        await self._task
        self._task = None

    async def _run(self) -> None:
        while not self._stop.is_set():
            try:
                await asyncio.wait_for(self._stop.wait(), timeout=self.interval)
                return
            except TimeoutError:
                pass
            try:
                token = await asyncio.to_thread(refresh_job, self.model, self.job_id, self.token)
            except Exception:
                logger.exception("Failed to renew database job claim")
                continue
            if token is None:
                return
            self.token = token

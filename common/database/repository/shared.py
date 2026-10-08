from collections.abc import Awaitable, Callable
from datetime import UTC, datetime, timedelta
from enum import StrEnum, auto
from typing import Any, cast

from sqlalchemy import CursorResult, and_, func, or_, update
from sqlmodel import col, select
from sqlmodel.ext.asyncio.session import AsyncSession

from common.database.postgres_models import JobStatus, Minute, MinuteVersion, Transcription


class ClaimState(StrEnum):
    CLAIMED = auto()
    COMPLETED = auto()
    IN_PROGRESS = auto()
    FAILED = auto()
    MISSING = auto()


def _stale_cutoff(stale_seconds: int) -> datetime:
    # Client-computed cutoff: claimed_at is written by the server clock, so this tolerates
    # small clock skew by design (the stale window is minutes, skew is seconds).
    return datetime.now(UTC) - timedelta(seconds=stale_seconds)


def _claimable(model: type, stale_seconds: int) -> Any:
    """WHERE clause of the claim CAS: claim rows that are waiting, or whose lease
    has expired (worker died mid-job - claimed_at stopped being refreshed because
    the SQS visibility heartbeat stopped)."""
    cutoff = _stale_cutoff(stale_seconds)
    return or_(
        model.status == JobStatus.AWAITING_START,
        and_(
            model.status == JobStatus.IN_PROGRESS,
            or_(model.claimed_at.is_(None), model.claimed_at < cutoff),
        ),
    )


async def claim_for_processing(
    session: AsyncSession,
    model: type,
    entity_id: Any,
    stale_seconds: int,
) -> ClaimState:
    """Atomic compare-and-swap claim.

    The UPDATE only matches rows in a claimable state, so two concurrent claimants
    cannot both win: exactly one sees rowcount=1. Binding JobStatus members through
    the table's column types persists their NAMES (AWAITING_START...), matching the
    native pg enum labels - never compare against StrEnum .value (lowercase).

    The caller owns the transaction (commit when it is safe to lose the message).
    """
    stmt = (
        update(model)
        .where(model.id == entity_id, _claimable(model, stale_seconds))
        .values(status=JobStatus.IN_PROGRESS, claimed_at=func.now())
    )
    result = cast(CursorResult, await session.execute(stmt))
    if result.rowcount:
        return ClaimState.CLAIMED
    row = (await session.execute(select(model.status).where(model.id == entity_id))).first()
    if row is None:
        return ClaimState.MISSING
    status = row[0]
    return {
        JobStatus.AWAITING_START: ClaimState.IN_PROGRESS,  # unclaimable yet somehow unclaimed
        JobStatus.IN_PROGRESS: ClaimState.IN_PROGRESS,
        JobStatus.COMPLETED: ClaimState.COMPLETED,
        JobStatus.FAILED: ClaimState.FAILED,
    }[status]


def make_finalizer(model: type, error_message: str) -> Callable[[AsyncSession, timedelta], Awaitable[int]]:
    """Bulk-sweep rows stuck IN_PROGRESS past the lease horizon (worker died and
    nothing ever re-claimed them) so users can hit retry instead of waiting forever."""

    async def finalize_stale(session: AsyncSession, older_than: timedelta) -> int:
        stmt = (
            update(model)
            .where(
                and_(
                    model.status == JobStatus.IN_PROGRESS,
                    or_(
                        model.claimed_at.is_(None),
                        model.claimed_at < datetime.now(UTC) - older_than,
                    ),
                )
            )
            .values(status=JobStatus.FAILED, error=error_message)
        )
        result = cast(CursorResult, await session.execute(stmt))
        return result.rowcount

    return finalize_stale


async def refresh_job_leases(session: AsyncSession, minute_version_id: Any) -> None:
    """Renew the leases of whichever of the job's rows are currently IN_PROGRESS.

    The consumer heartbeat calls this every interval, so a legitimately long job keeps
    its claim fresh and duplicate messages can never steal it - claimed_at staleness
    then means "no worker has heartbeated for this job", i.e. the worker died.
    Rows in terminal states are never touched (status-guarded), which also makes this
    a no-op for whichever phase has already completed.
    """
    await session.execute(
        update(MinuteVersion)
        .where(col(MinuteVersion.id) == minute_version_id, col(MinuteVersion.status) == JobStatus.IN_PROGRESS)
        .values(claimed_at=func.now())
    )
    transcription_ids = (
        select(Transcription.id)
        .select_from(MinuteVersion)
        .join(Minute, col(Minute.id) == col(MinuteVersion.minute_id))
        .join(Transcription, col(Transcription.id) == col(Minute.transcription_id))
        .where(col(MinuteVersion.id) == minute_version_id)
    )
    await session.execute(
        update(Transcription)
        .where(col(Transcription.id).in_(transcription_ids), col(Transcription.status) == JobStatus.IN_PROGRESS)
        .values(claimed_at=func.now())
    )

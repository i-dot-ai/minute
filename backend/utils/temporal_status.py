"""Bounded, aggregate reads from Temporal Visibility; no workflow history or payloads."""

import asyncio
import math
from datetime import UTC, datetime, timedelta
from time import monotonic

from temporalio.client import Client

from backend.utils.temporal import get_temporal_client
from common.types import StatusComponent, StatusCounts, StatusDistribution, StatusResponse, StatusSummary

_COMPONENTS = {
    "transcription": "TranscriptionWorkflow",
    "minute_generation": "MinuteGenerationWorkflow",
    "ai_edit": "MinuteEditWorkflow",
}
_CLOSED_STATUSES = {
    "Completed": "completed",
    "Failed": "failed",
    "TimedOut": "timed_out",
    "Canceled": "canceled",
    "Terminated": "terminated",
    "ContinuedAsNew": "continued_as_new",
}
_MAX_RUNS = 1_000
_RPC_TIMEOUT = timedelta(seconds=5)
_CACHE_SECONDS = 30
_lock = asyncio.Lock()
# shortcut: one cached horizon per process; use a bounded shared cache if varied horizons cause load.
_cache: tuple[int, float, StatusResponse] | None = None


def _distribution(values: list[float]) -> StatusDistribution:
    count = len(values)
    if not values or count > _MAX_RUNS:
        return StatusDistribution(sample_count=count, truncated=count > _MAX_RUNS)
    values = sorted(values)
    return StatusDistribution(
        sample_count=count,
        p50=values[math.ceil(count * 0.50) - 1],
        p90=values[math.ceil(count * 0.90) - 1],
        p99=values[math.ceil(count * 0.99) - 1],
        max=values[-1],
    )


async def _timings(client: Client, query: str, now: datetime) -> StatusDistribution:
    values = [
        ((run.close_time or now) - run.start_time).total_seconds()
        async for run in client.list_workflows(query, limit=_MAX_RUNS + 1, page_size=200, rpc_timeout=_RPC_TIMEOUT)
    ]
    return _distribution(values)


def _rates(counts: StatusCounts, horizon_seconds: int) -> tuple[float | None, float]:
    failures = counts.failed + counts.timed_out
    outcomes = counts.completed + failures
    return failures / outcomes if outcomes else None, counts.completed * 60 / horizon_seconds


async def _component(client: Client, workflow_type: str, start: datetime, end: datetime) -> StatusComponent:
    base = f'WorkflowType = "{workflow_type}"'
    started_query = f'{base} AND StartTime >= "{start.isoformat()}" AND StartTime < "{end.isoformat()}"'
    closed_query = f'{base} AND CloseTime >= "{start.isoformat()}" AND CloseTime < "{end.isoformat()}"'
    running_query = f'{base} AND ExecutionStatus = "Running" AND StartTime < "{end.isoformat()}"'
    async with asyncio.TaskGroup() as tasks:
        started = tasks.create_task(client.count_workflows(started_query, rpc_timeout=_RPC_TIMEOUT))
        closed = tasks.create_task(
            client.count_workflows(f"{closed_query} GROUP BY ExecutionStatus", rpc_timeout=_RPC_TIMEOUT)
        )
        running = tasks.create_task(client.count_workflows(running_query, rpc_timeout=_RPC_TIMEOUT))
        processing_time = tasks.create_task(_timings(client, f'{closed_query} AND ExecutionStatus = "Completed"', end))
        in_progress_age = tasks.create_task(_timings(client, running_query, end))

    closed_counts = {group.group_values[0]: group.count for group in closed.result().groups}
    counts = StatusCounts(
        started=started.result().count,
        in_progress=running.result().count,
        **{field: closed_counts.get(status, 0) for status, field in _CLOSED_STATUSES.items()},
    )
    failure_rate, throughput = _rates(counts, int((end - start).total_seconds()))
    return StatusComponent(
        workflow_type=workflow_type,
        counts=counts,
        failure_rate=failure_rate,
        completed_per_minute=throughput,
        processing_time_seconds=processing_time.result(),
        in_progress_age_seconds=in_progress_age.result(),
    )


async def _collect_status(horizon_seconds: int) -> StatusResponse:
    end = datetime.now(UTC)
    start = end - timedelta(seconds=horizon_seconds)
    client = await get_temporal_client()
    async with asyncio.TaskGroup() as tasks:
        pending = {
            name: tasks.create_task(_component(client, workflow_type, start, end))
            for name, workflow_type in _COMPONENTS.items()
        }
    components = {name: task.result() for name, task in pending.items()}
    counts = StatusCounts(
        **{
            field: sum(getattr(component.counts, field) for component in components.values())
            for field in StatusCounts.model_fields
        }
    )
    failure_rate, throughput = _rates(counts, horizon_seconds)
    return StatusResponse(
        horizon_seconds=horizon_seconds,
        window_start=start,
        window_end=end,
        collected_at=datetime.now(UTC),
        partial=any(
            component.processing_time_seconds.truncated or component.in_progress_age_seconds.truncated
            for component in components.values()
        ),
        summary=StatusSummary(**counts.model_dump(), failure_rate=failure_rate, completed_per_minute=throughput),
        components=components,
    )


async def get_status(horizon_seconds: int) -> StatusResponse:
    global _cache  # noqa: PLW0603
    async with asyncio.timeout(10), _lock:
        if _cache is not None and _cache[0] == horizon_seconds and monotonic() < _cache[1]:
            return _cache[2]
        response = await _collect_status(horizon_seconds)
        _cache = (horizon_seconds, monotonic() + _CACHE_SECONDS, response)
        return response

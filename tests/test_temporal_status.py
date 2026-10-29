"""Visibility aggregation without a Temporal server, workflow history or database."""

import asyncio
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest
from temporalio.client import WorkflowExecutionCount, WorkflowExecutionCountAggregationGroup

from backend.utils import temporal_status


@pytest.mark.parametrize(
    ("values", "expected"),
    [
        ([], (0, None, None, None, None, False)),
        ([8.0], (1, 8.0, 8.0, 8.0, 8.0, False)),
        (list(range(100, 0, -1)), (100, 50, 90, 99, 100, False)),
        ([1.0] * 1_001, (1_001, None, None, None, None, True)),
    ],
)
def test_percentiles_and_read_limit(values, expected):
    result = temporal_status._distribution(values)  # noqa: SLF001
    assert (result.sample_count, result.p50, result.p90, result.p99, result.max, result.truncated) == expected


@pytest.mark.asyncio
async def test_collection_uses_start_close_and_all_running_scopes(monkeypatch):
    now = datetime.now(UTC)
    queries = []

    async def count(query, *, rpc_timeout):
        assert rpc_timeout.total_seconds() > 0
        queries.append(query)
        if 'WorkflowType = "TranscriptionWorkflow"' not in query:
            return WorkflowExecutionCount(count=0, groups=[])
        if "GROUP BY ExecutionStatus" in query:
            return WorkflowExecutionCount(
                count=212,
                groups=[
                    WorkflowExecutionCountAggregationGroup(count=value, group_values=[status])
                    for status, value in {"Completed": 205, "Failed": 2, "TimedOut": 1, "Canceled": 4}.items()
                ],
            )
        return WorkflowExecutionCount(count=7 if 'ExecutionStatus = "Running"' in query else 10, groups=[])

    async def workflows(query, *, limit, page_size, rpc_timeout):
        assert limit == 1_001
        assert page_size == 200
        assert rpc_timeout.total_seconds() > 0
        queries.append(query)
        if 'WorkflowType = "TranscriptionWorkflow"' not in query:
            return
        if 'ExecutionStatus = "Completed"' in query:
            # Older starts must still contribute when the run closes inside the horizon.
            for _ in range(205):
                yield SimpleNamespace(start_time=now - timedelta(hours=1), close_time=now - timedelta(seconds=1))
        else:
            yield SimpleNamespace(start_time=now - timedelta(hours=2), close_time=None)

    client = Mock(count_workflows=AsyncMock(side_effect=count), list_workflows=Mock(side_effect=workflows))
    monkeypatch.setattr(temporal_status, "get_temporal_client", AsyncMock(return_value=client))
    response = await temporal_status._collect_status(600)  # noqa: SLF001

    transcription = response.components["transcription"]
    assert set(response.components) == {"transcription", "minute_generation", "ai_edit"}
    assert response.window_end - response.window_start == timedelta(minutes=10)
    assert transcription.counts.started == 10
    assert transcription.counts.in_progress == 7
    assert transcription.counts.canceled == 4
    assert transcription.failure_rate == pytest.approx(3 / 208)
    assert response.summary.failure_rate == pytest.approx(3 / 208)
    assert response.summary.completed_per_minute == 20.5
    assert transcription.processing_time_seconds.sample_count == 205
    assert transcription.processing_time_seconds.p50 == 3_599
    assert transcription.in_progress_age_seconds.p50 >= 7_200
    assert response.components["ai_edit"].failure_rate is None
    assert response.components["ai_edit"].processing_time_seconds.p99 is None
    assert response.partial is False
    running_queries = [query for query in queries if 'ExecutionStatus = "Running"' in query]
    closed_queries = [query for query in queries if "CloseTime" in query]
    started_queries = [query for query in queries if "StartTime >=" in query]
    assert len(running_queries) == 6
    assert all("StartTime >=" not in query for query in running_queries)
    assert all("CloseTime" not in query for query in running_queries)
    assert len(closed_queries) == 6
    assert all("StartTime >=" not in query for query in closed_queries)
    assert len(started_queries) == 3
    assert all("StartTime <" in query for query in started_queries)
    # Response must contain no execution identifiers or payloads.
    assert "workflow_id" not in response.model_dump_json()


@pytest.mark.asyncio
async def test_overflow_omits_timings_not_counts(monkeypatch):
    async def workflows(_query, **_kwargs):
        now = datetime.now(UTC)
        for _ in range(1_001):
            yield SimpleNamespace(start_time=now - timedelta(seconds=10), close_time=None)

    client = Mock(
        count_workflows=AsyncMock(return_value=WorkflowExecutionCount(count=2_000, groups=[])),
        list_workflows=Mock(side_effect=workflows),
    )
    monkeypatch.setattr(temporal_status, "get_temporal_client", AsyncMock(return_value=client))
    response = await temporal_status._collect_status(600)  # noqa: SLF001
    assert response.partial is True
    assert response.summary.in_progress == 6_000
    for component in response.components.values():
        assert component.in_progress_age_seconds.truncated is True
        assert component.in_progress_age_seconds.p99 is None


@pytest.mark.asyncio
async def test_cache_shares_refresh_expires_and_never_hides_failure(monkeypatch):
    monkeypatch.setattr(temporal_status, "_cache", None)
    clock = Mock(return_value=0)
    monkeypatch.setattr(temporal_status, "monotonic", clock)
    response = object()
    collect = AsyncMock(return_value=response)
    monkeypatch.setattr(temporal_status, "_collect_status", collect)

    results = await asyncio.gather(temporal_status.get_status(600), temporal_status.get_status(600))
    assert results == [response, response]
    collect.assert_awaited_once_with(600)
    await temporal_status.get_status(3_600)
    assert collect.await_count == 2
    clock.return_value = 31
    collect.side_effect = TimeoutError
    with pytest.raises(TimeoutError):
        await temporal_status.get_status(3_600)
    collect.side_effect = None
    assert await temporal_status.get_status(3_600) is response
    assert collect.await_count == 4

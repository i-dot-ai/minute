"""Visibility aggregation without a Temporal server, workflow history or database."""

import asyncio
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest
from temporalio.client import WorkflowExecutionCount, WorkflowExecutionCountAggregationGroup, WorkflowExecutionStatus

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


@pytest.mark.asyncio
@pytest.mark.parametrize("memo_key", [temporal_status.AUDIO_SECONDS_MEMO, "audio_seconds"])
async def test_hourly_buckets_by_close_time_with_audio_rate(monkeypatch, memo_key):
    this_hour = datetime(2026, 10, 30, 13, tzinfo=UTC)
    now = this_hour + timedelta(minutes=5)
    first = this_hour - timedelta(hours=23)
    recent_start = now - timedelta(minutes=10)
    monkeypatch.setattr(temporal_status, "datetime", Mock(now=Mock(return_value=now)))

    def run(status, closed, seconds, audio=None):
        memo = AsyncMock(side_effect=lambda key, default: audio if key == memo_key else default)
        return SimpleNamespace(
            status=status, start_time=closed - timedelta(seconds=seconds), close_time=closed, memo_value=memo
        )

    runs = [
        run(WorkflowExecutionStatus.COMPLETED, this_hour + timedelta(seconds=1), 120, audio=3_600),
        run(WorkflowExecutionStatus.COMPLETED, this_hour + timedelta(seconds=2), 30, audio=1_800),
        run(WorkflowExecutionStatus.COMPLETED, now - timedelta(minutes=1), 60),  # pre-deploy: no audio memo
        run(WorkflowExecutionStatus.FAILED, now - timedelta(minutes=2), 30),
        run(WorkflowExecutionStatus.TIMED_OUT, first, 10),
        run(WorkflowExecutionStatus.COMPLETED, recent_start, 30, audio=1_800),
        run(WorkflowExecutionStatus.CANCELED, now - timedelta(minutes=1), 10),
        run(WorkflowExecutionStatus.COMPLETED, now, 900, audio=3_600),
        run(WorkflowExecutionStatus.COMPLETED, now + timedelta(seconds=1), 900, audio=3_600),
    ]

    async def count(query, *, rpc_timeout):
        assert 'WorkflowType = "TranscriptionWorkflow"' in query
        assert query.endswith("GROUP BY ExecutionStatus")
        assert "StartTime" not in query
        assert rpc_timeout.total_seconds() > 0
        start = datetime.fromisoformat(query.split('CloseTime >= "')[1].split('"')[0])
        end = datetime.fromisoformat(query.split('CloseTime < "')[1].split('"')[0])
        assert end <= now
        matching = [r for r in runs if start <= r.close_time < end]
        return WorkflowExecutionCount(
            count=len(matching),
            groups=[
                WorkflowExecutionCountAggregationGroup(
                    count=sum(r.status == status for r in matching), group_values=[name]
                )
                for name, status in (
                    ("Completed", WorkflowExecutionStatus.COMPLETED),
                    ("Failed", WorkflowExecutionStatus.FAILED),
                    ("TimedOut", WorkflowExecutionStatus.TIMED_OUT),
                    ("Canceled", WorkflowExecutionStatus.CANCELED),
                )
                if any(r.status == status for r in matching)
            ],
        )

    async def workflows(query, *, limit, page_size, rpc_timeout):
        assert 'WorkflowType = "TranscriptionWorkflow"' in query
        assert f'CloseTime >= "{first.isoformat()}"' in query
        assert f'CloseTime < "{now.isoformat()}"' in query
        assert 'ExecutionStatus = "Completed"' in query
        assert limit == 20_001
        assert page_size == 1_000
        assert rpc_timeout.total_seconds() > 0
        for r in runs:
            if r.status == WorkflowExecutionStatus.COMPLETED and first <= r.close_time < now:
                yield r

    client = Mock(count_workflows=AsyncMock(side_effect=count), list_workflows=Mock(side_effect=workflows))
    monkeypatch.setattr(temporal_status, "get_temporal_client", AsyncMock(return_value=client))
    response = await temporal_status._collect_hourly()  # noqa: SLF001

    assert client.count_workflows.await_count == 25
    count_queries = [call.args[0] for call in client.count_workflows.await_args_list]
    for i in range(24):
        start = first + timedelta(hours=i)
        end = min(start + timedelta(hours=1), now)
        assert any(
            f'CloseTime >= "{start.isoformat()}" AND CloseTime < "{end.isoformat()}"' in query
            for query in count_queries
        )
    assert len(response.hours) == 24
    assert response.hours[-1].start == this_hour
    assert response.partial is False
    latest, oldest = response.hours[-1], response.hours[0]
    assert (latest.completed, latest.failed) == (3, 1)
    assert latest.failure_rate == pytest.approx(1 / 4)
    assert latest.avg_processing_seconds == 70
    assert latest.audio_hours == 1.5
    assert latest.processing_seconds_per_audio_hour == 100  # only runs with recorded audio
    rates = latest.per_audio_hour_seconds  # per run: 120s for 1h, 30s for 0.5h -> 120, 60
    assert (rates.sample_count, rates.p50, rates.p90, rates.p99, rates.max) == (2, 60, 120, 120, 120)
    assert (oldest.failed, oldest.failure_rate, oldest.avg_processing_seconds) == (1, 1.0, None)
    assert response.hours[5].failure_rate is None
    assert response.hours[5].processing_seconds_per_audio_hour is None
    assert response.hours[5].per_audio_hour_seconds.p50 is None
    recent = response.last_10_minutes
    assert recent.start == recent_start
    assert (recent.completed, recent.failed, recent.avg_processing_seconds) == (4, 1, 60)
    assert recent.failure_rate == 0.2
    assert recent.processing_seconds_per_audio_hour == 90
    assert recent.per_audio_hour_seconds.sample_count == 3
    assert response.hours[-2].completed == 1


@pytest.mark.asyncio
async def test_hourly_read_limit_keeps_counts_and_error_rates(monkeypatch):
    monkeypatch.setattr(temporal_status, "_MAX_HOURLY_RUNS", 2)
    this_hour = datetime(2026, 10, 30, 13, tzinfo=UTC)
    closed = this_hour + timedelta(minutes=30)
    now = closed + timedelta(minutes=1)
    monkeypatch.setattr(temporal_status, "datetime", Mock(now=Mock(return_value=now)))

    async def count(query, **_kwargs):
        if not any(
            f'CloseTime >= "{start.isoformat()}"' in query for start in (this_hour, now - timedelta(minutes=10))
        ):
            return WorkflowExecutionCount(count=0, groups=[])
        return WorkflowExecutionCount(
            count=2_600,
            groups=[
                WorkflowExecutionCountAggregationGroup(count=value, group_values=[status])
                for status, value in {"Completed": 2_000, "Failed": 500, "TimedOut": 100}.items()
            ],
        )

    async def workflows(query, **_kwargs):
        assert 'ExecutionStatus = "Completed"' in query
        for seconds in (10, 20, 900):
            yield SimpleNamespace(
                start_time=closed - timedelta(seconds=seconds),
                close_time=closed,
                memo_value=AsyncMock(return_value=3_600),
            )

    client = Mock(count_workflows=AsyncMock(side_effect=count), list_workflows=Mock(side_effect=workflows))
    monkeypatch.setattr(temporal_status, "get_temporal_client", AsyncMock(return_value=client))
    response = await temporal_status._collect_hourly()  # noqa: SLF001
    assert response.partial is True
    assert sum(hour.completed for hour in response.hours) == 2_000
    assert sum(hour.failed for hour in response.hours) == 600
    for bucket in (response.hours[-1], response.last_10_minutes):
        assert bucket.completed == 2_000
        assert bucket.failed == 600
        assert bucket.failure_rate == pytest.approx(600 / 2_600)
        assert bucket.avg_processing_seconds == 15  # Divide by listed runs, not the uncapped count.
        assert bucket.audio_hours == 2
        assert bucket.processing_seconds_per_audio_hour == 15
        assert bucket.per_audio_hour_seconds.sample_count == 2
        assert bucket.per_audio_hour_seconds.p50 == 10
        assert bucket.per_audio_hour_seconds.p90 == 20

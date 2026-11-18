"""The metrics activity and its projection, with Temporal Visibility and the metrics writer mocked."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock

import pytest
from temporalio import activity
from temporalio.testing import WorkflowEnvironment
from temporalio.worker import Worker

from common.types import StatusComponent, StatusCounts, StatusDistribution, StatusResponse, StatusSummary
from common.workflows.activities import emit_metrics
from common.workflows.metrics import MetricsWorkflow
from common.workflows.transcription import TASK_QUEUE


def _component(**overrides) -> StatusComponent:
    defaults = {
        "workflow_type": "TranscriptionWorkflow",
        "counts": StatusCounts(started=10, completed=7, failed=2, timed_out=1, in_progress=3),
        "failure_rate": 0.3,
        "completed_per_minute": 7.0,
        "processing_time_seconds": StatusDistribution(sample_count=7, p50=5.0, p90=9.0, p99=9.5, max=10.0),
        "in_progress_age_seconds": StatusDistribution(sample_count=3, p50=4.0, p90=8.0, p99=8.0, max=120.0),
    }
    return StatusComponent(**{**defaults, **overrides})


def test_component_metrics_cover_counts_rates_and_distributions():
    metrics = emit_metrics._component_metrics(_component())  # noqa: SLF001

    assert metrics["started"] == 10
    assert metrics["completed"] == 7
    assert metrics["failed"] == 3  # failed + timed_out
    assert metrics["in_progress"] == 3
    assert metrics["failure_rate"] == 0.3
    assert metrics["processing_time_p50_seconds"] == 5.0
    assert metrics["processing_time_p99_seconds"] == 9.5
    assert metrics["in_progress_max_age_seconds"] == 120.0


def test_component_metrics_drop_none_and_zero_values():
    """None (no data) and zero must both be absent: the shared writer rejects falsy values, and a
    missing datapoint lets the alarms tell an idle pipeline apart from a broken one."""
    component = _component(
        counts=StatusCounts(started=5, completed=0, failed=0, timed_out=0, in_progress=0),
        failure_rate=None,
        completed_per_minute=0.0,
        processing_time_seconds=StatusDistribution(sample_count=0),
        in_progress_age_seconds=StatusDistribution(sample_count=0),
    )
    metrics = emit_metrics._component_metrics(component)  # noqa: SLF001

    assert metrics == {"started": 5}  # every zero/None dropped, only the non-zero count remains


@pytest.mark.asyncio
async def test_activity_emits_prefixed_metrics_per_component(monkeypatch):
    response = StatusResponse(
        horizon_seconds=emit_metrics.HORIZON_SECONDS,
        window_start=datetime.now(UTC),
        window_end=datetime.now(UTC),
        collected_at=datetime.now(UTC),
        partial=False,
        summary=StatusSummary(failure_rate=0.3, completed_per_minute=7.0),
        components={"transcription": _component(), "minute_generation": _component(), "ai_edit": _component()},
    )
    monkeypatch.setattr(emit_metrics, "get_status", AsyncMock(return_value=response))
    writer = AsyncMock()
    writer.put_metric = lambda **kwargs: calls.append(kwargs)
    calls: list[dict] = []
    monkeypatch.setattr(emit_metrics, "_metrics_writer", lambda: writer)

    await emit_metrics.emit_temporal_metrics()

    names = {call["metric_name"] for call in calls}
    assert "temporal_transcription_failure_rate" in names
    assert "temporal_minute_generation_in_progress_max_age_seconds" in names
    assert "temporal_ai_edit_started" in names
    assert all(name.startswith("temporal_") for name in names)
    # Three components, each emitting the same ten non-zero/non-None metrics.
    assert len(calls) == 3 * 10


@pytest.mark.asyncio
async def test_workflow_drives_the_activity_in_the_sandbox():
    """Run MetricsWorkflow through a real sandboxed worker: proves the workflow module imports under
    the Temporal sandbox and that it calls the registered activity by name on the task queue."""
    called = False

    @activity.defn(name="emit_temporal_metrics")
    async def emit_temporal_metrics() -> None:
        nonlocal called
        called = True

    async with (
        await WorkflowEnvironment.start_time_skipping() as env,
        Worker(
            env.client,
            task_queue=TASK_QUEUE,
            workflows=[MetricsWorkflow],
            activities=[emit_temporal_metrics],
        ),
    ):
        await env.client.execute_workflow(MetricsWorkflow.run, id="metrics-test", task_queue=TASK_QUEUE)
    assert called

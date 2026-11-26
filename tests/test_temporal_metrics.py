"""The metrics activity and its projection, with Temporal Visibility and the metrics writer mocked."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock

import pytest
import pytest_asyncio
from i_dot_ai_utilities.metrics.unit import Unit
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


def _idle_component() -> StatusComponent:
    """A component that ran but produced only zeros and empty distributions: zero completions/failures,
    no failure_rate (nothing closed) and no timing samples."""
    return _component(
        counts=StatusCounts(started=5, completed=0, failed=0, timed_out=0, in_progress=0),
        failure_rate=None,
        completed_per_minute=0.0,
        processing_time_seconds=StatusDistribution(sample_count=0),
        in_progress_age_seconds=StatusDistribution(sample_count=0),
    )


@pytest.mark.parametrize(
    ("metric_name", "expected"),
    [
        ("started", 10),
        ("completed", 7),
        ("failed", 3),
        ("in_progress", 3),
        ("failure_rate", 30.0),  # 0.3 fraction emitted as a 0-100 percentage
        ("completed_per_minute", 7.0),
        ("processing_time_p50_seconds", 5.0),
        ("processing_time_p99_seconds", 9.5),
        ("in_progress_max_age_seconds", 120.0),
    ],
)
def test_component_metric_values(metric_name, expected):
    assert emit_metrics._component_metrics(_component())[metric_name][0] == expected  # noqa: SLF001


@pytest.mark.parametrize(
    ("metric_name", "expected_unit"),
    [
        ("started", Unit.Count),
        ("failure_rate", Unit.Percent),
        ("completed_per_minute", Unit.Count),
        ("processing_time_p50_seconds", Unit.Seconds),
        ("in_progress_max_age_seconds", Unit.Seconds),
    ],
)
def test_component_metric_units(metric_name, expected_unit):
    assert emit_metrics._component_metrics(_component())[metric_name][1] is expected_unit  # noqa: SLF001


def test_component_metrics_keep_meaningful_zeros():
    """Zeros are kept: a failure_rate of 0.0 or zero failures is a legitimate datapoint.
    (notBreaching) window."""
    metrics = emit_metrics._component_metrics(_idle_component())  # noqa: SLF001
    assert set(metrics) == {"started", "completed", "failed", "in_progress", "completed_per_minute"}


@pytest.mark.parametrize(("metric_name", "expected"), [("completed", 0), ("failed", 0), ("completed_per_minute", 0.0)])
def test_component_metrics_retain_zero_values(metric_name, expected):
    assert emit_metrics._component_metrics(_idle_component())[metric_name][0] == expected  # noqa: SLF001


@pytest.mark.parametrize("metric_name", ["failure_rate", "processing_time_p50_seconds"])
def test_component_metrics_drop_none_signals(metric_name):
    """None means no data (nothing closed, no timing samples) and must be absent entirely."""
    assert metric_name not in emit_metrics._component_metrics(_idle_component())  # noqa: SLF001


@pytest_asyncio.fixture
async def emitted_calls(monkeypatch) -> list[dict]:
    """Run the activity once against three components and capture every put_metric call."""
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
    calls: list[dict] = []
    writer = AsyncMock()
    writer.put_metric = lambda **kwargs: calls.append(kwargs)
    monkeypatch.setattr(emit_metrics, "_metrics_writer", lambda: writer)

    await emit_metrics.emit_temporal_metrics()
    return calls


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "metric_name",
    [
        "temporal_transcription_failure_rate",
        "temporal_minute_generation_in_progress_max_age_seconds",
        "temporal_ai_edit_started",
    ],
)
async def test_activity_emits_expected_metric_names(emitted_calls, metric_name):
    assert metric_name in {call["metric_name"] for call in emitted_calls}


@pytest.mark.asyncio
async def test_activity_prefixes_component_metrics(emitted_calls):
    component_metrics = [call for call in emitted_calls if call["metric_name"] != emit_metrics.HEARTBEAT_METRIC]
    assert component_metrics
    assert all(call["metric_name"].startswith("temporal_") for call in component_metrics)


@pytest.mark.asyncio
async def test_activity_emits_heartbeat_first(emitted_calls):
    """A single heartbeat is emitted unconditionally, before any per-component metric."""
    assert emitted_calls[0]["metric_name"] == emit_metrics.HEARTBEAT_METRIC
    assert emitted_calls[0]["value"] == 1


@pytest.mark.asyncio
async def test_activity_tags_every_metric_with_a_unit(emitted_calls):
    assert all(call["unit"] in set(Unit) for call in emitted_calls)


@pytest.mark.asyncio
async def test_activity_emits_one_heartbeat_plus_ten_per_component(emitted_calls):
    assert len(emitted_calls) == 1 + 3 * 10


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

"""EMF serialization and the metrics activity, with Temporal Visibility mocked out."""

import json
from datetime import UTC, datetime
from unittest.mock import AsyncMock

import pytest
from temporalio import activity
from temporalio.testing import WorkflowEnvironment
from temporalio.worker import Worker

from common.observability import cloudwatch_metrics
from common.observability.cloudwatch_metrics import Metric
from common.types import StatusComponent, StatusCounts, StatusDistribution, StatusResponse, StatusSummary
from common.workflows.activities import emit_metrics
from common.workflows.metrics import MetricsWorkflow
from common.workflows.transcription import TASK_QUEUE


def _capture_emf(capsys) -> list[dict]:
    """Parse the EMF lines written to stdout back into dicts."""
    out = capsys.readouterr().out
    return [json.loads(line) for line in out.splitlines() if line.strip()]


def test_emf_line_is_spec_shaped(capsys):
    cloudwatch_metrics.emit(
        "Minute/Temporal",
        {"Environment": "prod", "Component": "transcription"},
        [Metric("FailureRate", 0.25, "None"), Metric("StartedCount", 10, "Count")],
        timestamp_ms=1_700_000_000_000,
    )
    (line,) = _capture_emf(capsys)

    directive = line["_aws"]["CloudWatchMetrics"][0]
    assert line["_aws"]["Timestamp"] == 1_700_000_000_000
    assert directive["Namespace"] == "Minute/Temporal"
    # Dimensions are a list of one dimension set; both keys must also appear at the root.
    assert directive["Dimensions"] == [["Environment", "Component"]]
    assert {"Name": "FailureRate", "Unit": "None"} in directive["Metrics"]
    assert line["Environment"] == "prod"
    assert line["Component"] == "transcription"
    assert line["FailureRate"] == 0.25
    assert line["StartedCount"] == 10


def test_emit_writes_nothing_without_metrics(capsys):
    cloudwatch_metrics.emit("Minute/Temporal", {"Environment": "prod"}, [])
    assert _capture_emf(capsys) == []


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
    metrics = {m.name: m for m in emit_metrics._component_metrics(_component())}  # noqa: SLF001

    assert metrics["StartedCount"].value == 10
    assert metrics["CompletedCount"].value == 7
    assert metrics["FailedCount"].value == 3  # failed + timed_out
    assert metrics["InProgressCount"].value == 3
    assert metrics["FailureRate"].value == 0.3
    assert metrics["ProcessingTimeP50Seconds"].value == 5.0
    assert metrics["ProcessingTimeP99Seconds"].value == 9.5
    assert metrics["InProgressMaxAgeSeconds"].value == 120.0


def test_component_metrics_drop_none_valued_stats():
    """No outcomes and an empty timing distribution must be absent, not zero, so the alarms can
    treat an idle pipeline differently from a broken one."""
    component = _component(
        failure_rate=None,
        processing_time_seconds=StatusDistribution(sample_count=0),
        in_progress_age_seconds=StatusDistribution(sample_count=0),
    )
    names = {m.name for m in emit_metrics._component_metrics(component)}  # noqa: SLF001

    assert "FailureRate" not in names
    assert "ProcessingTimeP50Seconds" not in names
    assert "InProgressMaxAgeSeconds" not in names
    # Counts are always present, including explicit zeroes.
    assert {"StartedCount", "CompletedCount", "FailedCount", "InProgressCount", "CompletedPerMinute"} <= names


@pytest.mark.asyncio
async def test_activity_emits_one_line_per_component(capsys, monkeypatch):
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

    await emit_metrics.emit_temporal_metrics()

    lines = _capture_emf(capsys)
    assert {line["Component"] for line in lines} == {"transcription", "minute_generation", "ai_edit"}
    assert all(line["_aws"]["CloudWatchMetrics"][0]["Namespace"] == "Minute/Temporal" for line in lines)
    assert all(line["Environment"] for line in lines)


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

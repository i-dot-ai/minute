"""Collect Temporal pipeline health metrics and emit to CloudWatch via the metrics writer.

Takes the same status metrics we provide through the status API & pipes them over to CloudWatch
so we can alert on them - runs on a schedule (see worker/temporal_worker.py).
Note: Service health of Temporal _itself_ is monitored through ECS, this covers internal
temporal metrics so we have a sense of workflow/activity/task health rather than the overall
service uptime.
"""

import logging

from i_dot_ai_utilities.metrics.cloudwatch import CloudwatchEmbeddedMetricsWriter
from i_dot_ai_utilities.metrics.interfaces import MetricsWriter
from i_dot_ai_utilities.metrics.unit import Unit
from temporalio import activity

from common.observability.temporal_status import get_status
from common.settings import get_settings, get_structured_logger
from common.types import StatusComponent

logger = logging.getLogger(__name__)

HORIZON_SECONDS = 60
HEARTBEAT_METRIC = "temporal_metrics_heartbeat"


def _scale_to_percentage(fraction: float | None) -> float | None:
    """Turn a 0-1 fraction into a 0-100 percentage, preserving None (no data)."""
    return fraction * 100 if fraction is not None else None


def _metrics_writer() -> MetricsWriter:
    settings = get_settings()
    return CloudwatchEmbeddedMetricsWriter(
        namespace=settings.REPO,
        environment=settings.ENVIRONMENT,
        logger=get_structured_logger(),
    )


def _component_metrics(component: StatusComponent) -> dict[str, tuple[float, Unit]]:
    """The metric name & (value, unit) tuples for one workflow type.

    `None` values are dropped, zeros are kept as a legitimate value
    """
    counts = component.counts
    processing = component.processing_time_seconds
    backlog = component.in_progress_age_seconds
    candidates: dict[str, tuple[float | None, Unit]] = {
        "started": (counts.started, Unit.Count),
        "completed": (counts.completed, Unit.Count),
        "failed": (counts.failed + counts.timed_out, Unit.Count),
        "in_progress": (counts.in_progress, Unit.Count),
        "completed_per_minute": (component.completed_per_minute, Unit.Count),
        "failure_rate": (_scale_to_percentage(component.failure_rate), Unit.Percent),
        "processing_time_p50_seconds": (processing.p50, Unit.Seconds),
        "processing_time_p90_seconds": (processing.p90, Unit.Seconds),
        "processing_time_p99_seconds": (processing.p99, Unit.Seconds),
        "in_progress_max_age_seconds": (backlog.max, Unit.Seconds),
    }
    return {name: (value, unit) for name, (value, unit) in candidates.items() if value is not None}


@activity.defn
async def emit_temporal_metrics() -> None:
    """Read pipeline health over the recent window and emit per-component metrics to CloudWatch."""
    writer = _metrics_writer()
    writer.put_metric(metric_name=HEARTBEAT_METRIC, value=1, unit=Unit.Count)
    status = await get_status(HORIZON_SECONDS)
    for component_name, component in status.components.items():
        for metric_name, (value, unit) in _component_metrics(component).items():
            writer.put_metric(metric_name=f"temporal_{component_name}_{metric_name}", value=value, unit=unit)
    logger.info("Emitted Temporal pipeline metrics for %d components", len(status.components))

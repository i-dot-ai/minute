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
from temporalio import activity

from common.observability.temporal_status import get_status
from common.settings import get_settings, get_structured_logger
from common.types import StatusComponent

logger = logging.getLogger(__name__)

HORIZON_SECONDS = 60


def _metrics_writer() -> MetricsWriter:
    settings = get_settings()
    return CloudwatchEmbeddedMetricsWriter(
        namespace=settings.REPO,
        environment=settings.ENVIRONMENT,
        logger=get_structured_logger(),
    )


def _component_metrics(component: StatusComponent) -> dict[str, float]:
    """The metric name -> value pairs for one workflow type."""
    counts = component.counts
    processing = component.processing_time_seconds
    backlog = component.in_progress_age_seconds
    candidates: dict[str, float | None] = {
        "started": counts.started,
        "completed": counts.completed,
        "failed": counts.failed + counts.timed_out,
        "in_progress": counts.in_progress,
        "completed_per_minute": component.completed_per_minute,
        "failure_rate": component.failure_rate,
        "processing_time_p50_seconds": processing.p50,
        "processing_time_p90_seconds": processing.p90,
        "processing_time_p99_seconds": processing.p99,
        "in_progress_max_age_seconds": backlog.max,
    }
    return {name: value for name, value in candidates.items() if value}


@activity.defn
async def emit_temporal_metrics() -> None:
    """Read pipeline health over the recent window and emit per-component metrics to CloudWatch."""
    writer = _metrics_writer()
    status = await get_status(HORIZON_SECONDS)
    for component_name, component in status.components.items():
        for metric_name, value in _component_metrics(component).items():
            writer.put_metric(metric_name=f"temporal_{component_name}_{metric_name}", value=value)
    logger.info("Emitted Temporal pipeline metrics for %d components", len(status.components))

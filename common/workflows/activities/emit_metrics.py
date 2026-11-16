"""Collect Temporal pipeline health from visibility and emit it to CloudWatch as EMF metrics.

Takes the same status metrics we provide through the status API & pipes them over to CloudWatch
so we can alert on them - runs on a schedule (see worker/temporal_worker.py).
Note: Service health of Temporal _itself_ is monitored through ECS, this covers internal
temporal metrics so we have a sense of workflow/activity/task health rather than the overall
service uptime.
"""

import logging

from temporalio import activity

from common.observability import cloudwatch_metrics
from common.observability.cloudwatch_metrics import Metric
from common.observability.temporal_status import get_status
from common.settings import get_settings
from common.types import StatusComponent

logger = logging.getLogger(__name__)

NAMESPACE = "Minute/Temporal"
HORIZON_SECONDS = 60


def _component_metrics(component: StatusComponent) -> list[Metric]:
    """EMF metrics for one workflow type."""
    counts = component.counts
    processing = component.processing_time_seconds
    backlog = component.in_progress_age_seconds
    candidates = [
        Metric("StartedCount", counts.started, "Count"),
        Metric("CompletedCount", counts.completed, "Count"),
        Metric("FailedCount", counts.failed + counts.timed_out, "Count"),
        Metric("InProgressCount", counts.in_progress, "Count"),
        Metric("CompletedPerMinute", component.completed_per_minute, "Count/Second"),
        None if component.failure_rate is None else Metric("FailureRate", component.failure_rate, "None"),
        None if processing.p50 is None else Metric("ProcessingTimeP50Seconds", processing.p50, "Seconds"),
        None if processing.p90 is None else Metric("ProcessingTimeP90Seconds", processing.p90, "Seconds"),
        None if processing.p99 is None else Metric("ProcessingTimeP99Seconds", processing.p99, "Seconds"),
        None if backlog.max is None else Metric("InProgressMaxAgeSeconds", backlog.max, "Seconds"),
    ]
    return [metric for metric in candidates if metric is not None]


@activity.defn
async def emit_temporal_metrics() -> None:
    """Read pipeline health over the recent window and write one EMF line per workflow component."""
    environment = get_settings().ENVIRONMENT
    status = await get_status(HORIZON_SECONDS)
    for name, component in status.components.items():
        cloudwatch_metrics.emit(
            NAMESPACE,
            {"Environment": environment, "Component": name},
            _component_metrics(component),
        )
    logger.info("Emitted Temporal pipeline metrics for %d components", len(status.components))

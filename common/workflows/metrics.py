"""Periodic emission of Temporal pipeline metrics to CloudWatch."""

from datetime import timedelta

from temporalio import workflow
from temporalio.common import RetryPolicy

from common.workflows.transcription import TASK_QUEUE

_METRICS_RETRY = RetryPolicy(
    initial_interval=timedelta(seconds=5),
    backoff_coefficient=2.0,
    maximum_interval=timedelta(seconds=20),
    maximum_attempts=3,
)


@workflow.defn
class MetricsWorkflow:
    @workflow.run
    async def run(self) -> None:
        await workflow.execute_activity(
            "emit_temporal_metrics",
            task_queue=TASK_QUEUE,
            start_to_close_timeout=timedelta(seconds=30),
            retry_policy=_METRICS_RETRY,
        )

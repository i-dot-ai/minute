"""Daily cleanup orchestration; database and storage I/O stay in activities."""

from datetime import timedelta

from temporalio import workflow
from temporalio.common import RetryPolicy

from common.workflows.transcription import DB_RETRY, TASK_QUEUE

_STORAGE_RETRY = RetryPolicy(
    initial_interval=timedelta(seconds=10),
    backoff_coefficient=2.0,
    maximum_interval=timedelta(minutes=2),
    maximum_attempts=5,
)


@workflow.defn
class CleanupWorkflow:
    @workflow.run
    async def run(self) -> None:
        await workflow.execute_activity(
            "cleanup_old_records",
            task_queue=TASK_QUEUE,
            start_to_close_timeout=timedelta(minutes=30),
            retry_policy=DB_RETRY,
        )
        await workflow.execute_activity(
            "delete_orphan_records",
            task_queue=TASK_QUEUE,
            start_to_close_timeout=timedelta(minutes=30),
            heartbeat_timeout=timedelta(minutes=5),
            retry_policy=_STORAGE_RETRY,
        )
        await workflow.execute_activity(
            "cleanup_failed_records",
            task_queue=TASK_QUEUE,
            start_to_close_timeout=timedelta(minutes=30),
            retry_policy=DB_RETRY,
        )

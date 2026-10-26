"""Minute-version workflows: generation for user-created minutes, and AI edits.

Both wrap one MinuteHandlerService handler — the work the SQS LLM queue used to dispatch. The
activities live in common/workflows/activities/ and run on the shared LLM task queue (capped by
MAX_LLM_PROCESSES).
"""

from dataclasses import dataclass
from datetime import timedelta

from temporalio import workflow

from common.workflows.transcription import LLM_RETRY, LLM_TASK_QUEUE

GENERATE_MINUTE = "generate_minute"
EDIT_MINUTE = "edit_minute"
MINUTE_VERSION_TIMEOUT = timedelta(minutes=30)


@dataclass
class MinuteEditInput:
    minute_version_id: str
    source_minute_version_id: str


def workflow_id(minute_version_id: str) -> str:
    return f"minute-version-{minute_version_id}"


@workflow.defn(name="MinuteGenerationWorkflow")
class MinuteGenerationWorkflow:
    @workflow.run
    async def run(self, minute_version_id: str) -> None:
        await workflow.execute_activity(
            GENERATE_MINUTE,
            minute_version_id,
            task_queue=LLM_TASK_QUEUE,
            start_to_close_timeout=MINUTE_VERSION_TIMEOUT,
            retry_policy=LLM_RETRY,
        )


@workflow.defn(name="MinuteEditWorkflow")
class MinuteEditWorkflow:
    @workflow.run
    async def run(self, params: MinuteEditInput) -> None:
        await workflow.execute_activity(
            EDIT_MINUTE,
            params,
            task_queue=LLM_TASK_QUEUE,
            start_to_close_timeout=MINUTE_VERSION_TIMEOUT,
            retry_policy=LLM_RETRY,
        )

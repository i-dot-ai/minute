"""Minute-version workflows: generation for user-created minutes, and AI edits.

Both wrap one MinuteHandlerService handler — the work the SQS LLM queue used to dispatch. The
activities live in common/workflows/activities/ and run on the shared LLM task queue (capped by
MAX_LLM_PROCESSES).
"""

from dataclasses import dataclass
from datetime import timedelta

from temporalio import workflow
from temporalio.exceptions import ActivityError

from common.workflows.transcription import DB_RETRY, LLM_RETRY, LLM_TASK_QUEUE, TASK_QUEUE

GENERATE_MINUTE = "generate_minute"
EDIT_MINUTE = "edit_minute"
FAIL_MINUTE_VERSION = "fail_minute_version"
MINUTE_VERSION_TIMEOUT = timedelta(minutes=30)


@dataclass
class MinuteEditInput:
    minute_version_id: str
    source_minute_version_id: str


@dataclass
class FailMinuteInput:
    minute_version_id: str
    error: str


def workflow_id(minute_version_id: str) -> str:
    return f"minute-version-{minute_version_id}"


async def _execute(step: str, arg: str | MinuteEditInput, minute_version_id: str) -> None:
    try:
        await workflow.execute_activity(
            step,
            arg,
            task_queue=LLM_TASK_QUEUE,
            start_to_close_timeout=MINUTE_VERSION_TIMEOUT,
            retry_policy=LLM_RETRY,
        )
    except ActivityError as e:
        await workflow.execute_activity(
            FAIL_MINUTE_VERSION,
            FailMinuteInput(minute_version_id=minute_version_id, error=str(e.cause)),
            task_queue=TASK_QUEUE,
            start_to_close_timeout=timedelta(seconds=30),
            retry_policy=DB_RETRY,
        )
        raise


@workflow.defn(name="MinuteGenerationWorkflow")
class MinuteGenerationWorkflow:
    @workflow.run
    async def run(self, minute_version_id: str) -> None:
        await _execute(GENERATE_MINUTE, minute_version_id, minute_version_id)


@workflow.defn(name="MinuteEditWorkflow")
class MinuteEditWorkflow:
    @workflow.run
    async def run(self, params: MinuteEditInput) -> None:
        await _execute(EDIT_MINUTE, params, params.minute_version_id)

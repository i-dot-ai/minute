"""Transcription workflow. Deterministic orchestration only: no I/O, no service imports.

Activities are referenced by name so the workflow sandbox never imports the
transcription stack (ffmpeg, DB, LLM clients). They run in worker/temporal_activities.py
and pass only ids: transcripts and summaries stay in Postgres.
"""

from datetime import timedelta

from temporalio import workflow
from temporalio.common import RetryPolicy
from temporalio.exceptions import ActivityError

# One task queue per limited resource. A queue's worker slot count is that resource's cap:
# total concurrency = slots x worker processes polling the queue (worker/temporal_worker.py).
TASK_QUEUE = "transcription"  # workflow tasks + complete_transcription (fast DB write, uncapped)
STT_TASK_QUEUE = "stt"  # transcribe: Azure STT, capped by STT_MAX_CONCURRENCY
LLM_TASK_QUEUE = "llm"  # speakers, title, summary: shared Gemini quota, capped by MAX_LLM_PROCESSES

TRANSCRIBE = "transcribe"
IDENTIFY_SPEAKERS = "identify_speakers"
GENERATE_TITLE = "generate_title"
COMPLETE_TRANSCRIPTION = "complete_transcription"
SUMMARIZE = "summarize"

# Initial interval > 0 on claim-based steps so a retry after a crashed attempt waits for
# its DB claim (CLAIM_STALE_AFTER = 3 min) to go stale; until then the activity raises.
_CLAIMED_STEP_RETRY = RetryPolicy(
    initial_interval=timedelta(minutes=1),
    backoff_coefficient=2.0,
    maximum_interval=timedelta(minutes=5),
    maximum_attempts=10,
)
# The LLM client already retries each call (tenacity), so a few attempts here is enough.
_LLM_RETRY = RetryPolicy(
    initial_interval=timedelta(seconds=5), maximum_interval=timedelta(minutes=1), maximum_attempts=3
)
_DB_RETRY = RetryPolicy(
    initial_interval=timedelta(seconds=1), maximum_interval=timedelta(seconds=30), maximum_attempts=10
)


def workflow_id(transcription_id: str) -> str:
    return f"transcription-{transcription_id}"


@workflow.defn(name="TranscriptionWorkflow")
class TranscriptionWorkflow:
    @workflow.run
    async def run(self, minute_id: str) -> dict[str, str]:
        """Returns the outcome of each optional step, e.g. {"title": "failed: ..."}."""
        transcription_id: str = await workflow.execute_activity(
            TRANSCRIBE,
            minute_id,
            task_queue=STT_TASK_QUEUE,
            # Azure's own tenacity retries plus region failover can exceed an hour.
            start_to_close_timeout=timedelta(hours=2),
            heartbeat_timeout=timedelta(minutes=2),
            retry_policy=_CLAIMED_STEP_RETRY,
        )

        outcome: dict[str, str] = {}
        # Speaker naming before title: the title is generated from the named transcript.
        for step in (IDENTIFY_SPEAKERS, GENERATE_TITLE):
            outcome[step] = await self._optional(step, transcription_id, timedelta(minutes=10), _LLM_RETRY)

        completed: bool = await workflow.execute_activity(
            COMPLETE_TRANSCRIPTION,
            transcription_id,
            task_queue=TASK_QUEUE,
            start_to_close_timeout=timedelta(seconds=30),
            retry_policy=_DB_RETRY,
        )
        if not completed:
            outcome[SUMMARIZE] = "skipped: transcription deleted or no longer in progress"
            return outcome

        # A failed summary marks its minute_version FAILED (shown in the UI); the transcript stands.
        outcome[SUMMARIZE] = await self._optional(SUMMARIZE, minute_id, timedelta(minutes=30), _CLAIMED_STEP_RETRY)
        return outcome

    async def _optional(self, step: str, arg: str, start_to_close: timedelta, retry: RetryPolicy) -> str:
        """Optional LLM steps degrade: a failure is recorded in the outcome and the run carries on."""
        try:
            await workflow.execute_activity(
                step,
                arg,
                task_queue=LLM_TASK_QUEUE,
                start_to_close_timeout=start_to_close,
                heartbeat_timeout=timedelta(minutes=2),
                retry_policy=retry,
            )
        except ActivityError as e:
            workflow.logger.warning("Optional step %s failed: %s", step, e.cause)
            return f"failed: {e.cause}"
        return "ok"

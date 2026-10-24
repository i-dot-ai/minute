"""Transcription workflow. Deterministic orchestration only: no I/O, no service imports.

Activities are referenced by name so the workflow sandbox never imports the
transcription stack (ffmpeg, DB, LLM clients). They run in common/workflows/activities/
and pass only ids and small values: transcripts and summaries stay in Postgres.

No heartbeats: every step has a start_to_close timeout above its slowest healthy run, and
the SDK cancels an attempt locally when it expires. The STT step's timeout scales with the
audio duration measured by prepare_audio.
"""

import asyncio
from dataclasses import dataclass
from datetime import timedelta

from temporalio import workflow
from temporalio.common import RetryPolicy
from temporalio.exceptions import ActivityError

# One task queue per limited resource. A queue's worker slot count is that resource's cap:
# total concurrency = slots x worker processes polling the queue (worker/temporal_worker.py).
TASK_QUEUE = "transcription"  # workflow tasks + DB status writes (fast, uncapped)
STT_TASK_QUEUE = "stt"  # prepare_audio + transcribe: ffmpeg and Azure STT, capped by STT_MAX_CONCURRENCY
LLM_TASK_QUEUE = "llm"  # speakers, title, summary: shared Gemini quota, capped by MAX_LLM_PROCESSES

PREPARE_AUDIO = "prepare_audio"
TRANSCRIBE = "transcribe"
FAIL_TRANSCRIPTION = "fail_transcription"
IDENTIFY_SPEAKERS = "identify_speakers"
GENERATE_TITLE = "generate_title"
COMPLETE_TRANSCRIPTION = "complete_transcription"
SUMMARIZE = "summarize"

# STT timeout = floor + factor x audio duration. Measured: Azure took 119s for a 2h file (~2% of
# the duration), so 10% is ~5x headroom; the floor covers download, upload and short files.
# 2h audio -> 17 min, 5h (Azure's limit) -> 35 min.
STT_TIMEOUT_FLOOR = timedelta(minutes=5)
STT_TIMEOUT_PER_AUDIO_SECOND = 0.1
# Part of the STT activity timeout kept back from Azure's budget for the mp3 download, so a slow
# Azure fails as a retryable TranscriptionTransientError rather than an activity timeout.
STT_DOWNLOAD_MARGIN = timedelta(minutes=1)

# STT is the only retry loop (the provider never retries): each attempt makes one Azure request,
# on the region chosen from the attempt number (Azure.region_for), so the retries fan out across
# regions. 6 attempts over 3 regions gives each region two tries.
_STT_RETRY = RetryPolicy(
    initial_interval=timedelta(seconds=30),
    backoff_coefficient=2.0,
    maximum_interval=timedelta(minutes=2),
    maximum_attempts=6,
)
# prepare_audio (download + ffmpeg): a couple of quick retries for transient S3/ffmpeg hiccups.
_PREPARE_RETRY = RetryPolicy(
    initial_interval=timedelta(seconds=10), maximum_interval=timedelta(minutes=1), maximum_attempts=3
)
# Claim-based steps (summary, and the edit workflow): wait for a crashed attempt's claim
# (CLAIM_STALE_AFTER = 3 min) to go stale before retrying.
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


@dataclass
class PreparedAudio:
    duration_seconds: float


@dataclass
class TranscribeInput:
    minute_id: str
    stt_timeout_seconds: float


@dataclass
class FailTranscriptionInput:
    minute_id: str
    error: str


def workflow_id(transcription_id: str) -> str:
    return f"transcription-{transcription_id}"


def stt_timeout(duration_seconds: float) -> timedelta:
    return STT_TIMEOUT_FLOOR + timedelta(seconds=duration_seconds * STT_TIMEOUT_PER_AUDIO_SECOND)


@workflow.defn(name="TranscriptionWorkflow")
class TranscriptionWorkflow:
    @workflow.run
    async def run(self, minute_id: str) -> dict[str, str]:
        """Returns the outcome of each optional step, e.g. {"title": "failed: ..."}."""
        try:
            transcription_id = await self._transcribe(minute_id)
        except ActivityError as e:
            # Retries exhausted (or a non-retryable failure): don't leave the row IN_PROGRESS.
            await workflow.execute_activity(
                FAIL_TRANSCRIPTION,
                FailTranscriptionInput(minute_id=minute_id, error=str(e.cause)),
                task_queue=TASK_QUEUE,
                start_to_close_timeout=timedelta(seconds=30),
                retry_policy=_DB_RETRY,
            )
            raise

        outcome: dict[str, str] = {}
        # Speaker naming before title and summary: both are generated from the named transcript.
        outcome[IDENTIFY_SPEAKERS] = await self._optional(
            IDENTIFY_SPEAKERS, transcription_id, timedelta(minutes=10), _LLM_RETRY
        )

        completed: bool = await workflow.execute_activity(
            COMPLETE_TRANSCRIPTION,
            transcription_id,
            task_queue=TASK_QUEUE,
            start_to_close_timeout=timedelta(seconds=30),
            retry_policy=_DB_RETRY,
        )
        if not completed:
            skipped = "skipped: transcription deleted or no longer in progress"
            outcome[GENERATE_TITLE] = skipped
            outcome[SUMMARIZE] = skipped
            return outcome

        # The transcript is usable from here. The two steps write separate rows and don't depend on
        # each other, so they run together. Each degrades on failure: a failed summary marks its
        # minute_version FAILED (shown in the UI) while the transcript stands.
        outcome[GENERATE_TITLE], outcome[SUMMARIZE] = await asyncio.gather(
            self._optional(GENERATE_TITLE, transcription_id, timedelta(minutes=10), _LLM_RETRY),
            self._optional(SUMMARIZE, minute_id, timedelta(minutes=30), _CLAIMED_STEP_RETRY),
        )
        return outcome

    async def _transcribe(self, minute_id: str) -> str:
        audio: PreparedAudio = await workflow.execute_activity(
            PREPARE_AUDIO,
            minute_id,
            result_type=PreparedAudio,
            task_queue=STT_TASK_QUEUE,
            start_to_close_timeout=timedelta(minutes=10),  # 2h wav converted in ~22s
            retry_policy=_PREPARE_RETRY,
        )
        timeout = stt_timeout(audio.duration_seconds)
        return await workflow.execute_activity(
            TRANSCRIBE,
            TranscribeInput(
                minute_id=minute_id,
                stt_timeout_seconds=(timeout - STT_DOWNLOAD_MARGIN).total_seconds(),
            ),
            result_type=str,
            task_queue=STT_TASK_QUEUE,
            # One Azure request (one region) per attempt; Temporal's retry policy walks the regions.
            start_to_close_timeout=timeout,
            retry_policy=_STT_RETRY,
        )

    async def _optional(self, step: str, arg: str, start_to_close: timedelta, retry: RetryPolicy) -> str:
        """Optional LLM steps degrade: a failure is recorded in the outcome and the run carries on."""
        try:
            await workflow.execute_activity(
                step,
                arg,
                task_queue=LLM_TASK_QUEUE,
                start_to_close_timeout=start_to_close,
                retry_policy=retry,
            )
        except ActivityError as e:
            workflow.logger.warning("Optional step %s failed: %s", step, e.cause)
            return f"failed: {e.cause}"
        return "ok"

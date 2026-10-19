"""Temporal activities for the transcription workflow (common/workflows/transcription.py).

Each step is its own activity and passes only ids; content stays in Postgres (DB schema
unchanged). The transcription row stays IN_PROGRESS from `transcribe` until
`complete_transcription`, so the existing PATCH 409 guard keeps user edits out while the
post-processing steps write to it.
"""

import asyncio
import contextlib
from collections.abc import AsyncIterator
from uuid import UUID

from temporalio import activity
from temporalio.exceptions import ApplicationError

from common.audio.speakers import process_speakers_and_dialogue_entries
from common.database.postgres_models import JobStatus, Transcription
from common.generate_meeting_title import generate_meeting_title
from common.services.exceptions import TranscriptionFailedError
from common.services.minute_handler_service import MinuteDelivery, MinuteGenerationFailedError, MinuteHandlerService
from common.services.posthog_client import capture_event
from common.services.transcription_handler_service import TranscriptionHandlerService
from common.settings import get_structured_logger
from common.workflows import transcription as wf

slogger = get_structured_logger()

HEARTBEAT_INTERVAL_SECONDS = 30


@contextlib.asynccontextmanager
async def _heartbeating() -> AsyncIterator[None]:
    """Heartbeat while a step awaits a long external call (STT, LLM)."""

    async def _beat() -> None:
        while True:
            activity.heartbeat()
            await asyncio.sleep(HEARTBEAT_INTERVAL_SECONDS)

    task = asyncio.create_task(_beat())
    try:
        yield
    finally:
        task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await task


def _in_progress(transcription_id: UUID) -> Transcription | None:
    """The row if post-processing may still write to it; None if deleted, failed or done."""
    row = TranscriptionHandlerService.get_transcription_row(transcription_id)
    if row is None or row.status != JobStatus.IN_PROGRESS:
        slogger.info("Transcription no longer in progress; skipping step")
        return None
    return row


@activity.defn(name=wf.TRANSCRIBE)
async def transcribe(minute_id: str) -> str:
    """Download, convert, call the STT provider and save the raw transcript. Returns the transcription id."""
    mid = UUID(minute_id)
    slogger.refresh_context()
    slogger.set_context_field("minute_id", minute_id)
    try:
        async with _heartbeating():
            job = await TranscriptionHandlerService.process_transcription(minute_id=mid, post_process=False)
    except TranscriptionFailedError as e:
        # Row is already FAILED in the DB; retrying would only no-op.
        raise ApplicationError(str(e), non_retryable=True) from e

    if job is not None and not job.transcript:
        # ponytail: async (AWS) providers still re-queue via SQS; the worker refuses to start with them.
        msg = "Async transcription provider not supported on Temporal"
        raise ApplicationError(msg, non_retryable=True)

    transcription = TranscriptionHandlerService.get_transcription_from_minute_id(mid)
    if job is not None or transcription.status == JobStatus.COMPLETED:
        return str(transcription.id)

    # Claim lost: an earlier attempt of this activity owns (or owned) the row.
    if transcription.status == JobStatus.IN_PROGRESS and transcription.dialogue_entries:
        return str(transcription.id)  # it saved the transcript, then died before reporting
    if transcription.status == JobStatus.IN_PROGRESS:
        msg = "Transcription claimed by an earlier attempt; retrying once the claim goes stale"
        raise ApplicationError(msg)
    msg = f"Transcription is {transcription.status}; nothing to do"
    raise ApplicationError(msg, non_retryable=True)


@activity.defn(name=wf.IDENTIFY_SPEAKERS)
async def identify_speakers(transcription_id: str) -> None:
    tid = UUID(transcription_id)
    row = _in_progress(tid)
    if row is None or not row.dialogue_entries:
        return
    # ponytail: no separate raw transcript column, so a retry after a successful write
    # re-labels already-named entries; store raw.json in S3 (architecture §4) to make this pure.
    async with _heartbeating():
        named = await process_speakers_and_dialogue_entries(row.dialogue_entries)
    TranscriptionHandlerService.update_in_progress_transcription(tid, dialogue_entries=named)


@activity.defn(name=wf.GENERATE_TITLE)
async def generate_title(transcription_id: str) -> None:
    tid = UUID(transcription_id)
    row = _in_progress(tid)
    if row is None or not row.dialogue_entries:
        return
    async with _heartbeating():
        title = await generate_meeting_title(transcript=row.dialogue_entries)
    if title:
        TranscriptionHandlerService.update_in_progress_transcription(tid, title=title)


@activity.defn(name=wf.COMPLETE_TRANSCRIPTION)
async def complete_transcription(transcription_id: str) -> bool:
    """IN_PROGRESS -> COMPLETED. Idempotent: True if already COMPLETED, False if deleted/failed."""
    tid = UUID(transcription_id)
    if TranscriptionHandlerService.update_in_progress_transcription(tid, status=JobStatus.COMPLETED):
        row = TranscriptionHandlerService.get_transcription_row(tid)
        if row:
            capture_event(row.user_id, "transcription_succeeded", {"transcriptionId": transcription_id})
        return True
    row = TranscriptionHandlerService.get_transcription_row(tid)
    return row is not None and row.status == JobStatus.COMPLETED


@activity.defn(name=wf.SUMMARIZE)
async def summarize(minute_id: str) -> None:
    """Generate the initial minute version (same code the Ray LLM actor runs for MINUTE messages)."""
    slogger.refresh_context()
    slogger.set_context_field("minute_id", minute_id)
    try:
        minute_version = await MinuteHandlerService.get_only_minute_version_for_minute_id(UUID(minute_id))
    except ValueError as e:
        # Minute deleted with its transcription, or already edited: nothing to generate.
        raise ApplicationError(str(e), non_retryable=True) from e
    try:
        async with _heartbeating():
            delivery = await MinuteHandlerService.process_minute_generation_message(minute_version.id)
    except MinuteGenerationFailedError as e:
        # minute_version is already FAILED in the DB.
        raise ApplicationError(str(e.__cause__ or e), non_retryable=True) from e
    if delivery == MinuteDelivery.LEAVE:
        msg = "Minute version claimed by an earlier attempt; retrying once the claim goes stale"
        raise ApplicationError(msg)


# Grouped by task queue (common/workflows/transcription.py); each group is one Worker.
STT_ACTIVITIES = [transcribe]  # the only Azure caller
LLM_ACTIVITIES = [identify_speakers, generate_title, summarize]  # the only Gemini callers
WORKFLOW_QUEUE_ACTIVITIES = [complete_transcription]

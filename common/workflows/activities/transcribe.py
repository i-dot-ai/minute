"""Activity: one STT call on the prepared mp3, saving the raw transcript."""

import asyncio
from contextlib import suppress
from uuid import UUID

from temporalio import activity
from temporalio.exceptions import ApplicationError

from common.database.postgres_models import JobStatus, Transcription
from common.services.errors import is_transient
from common.services.exceptions import TranscriptionFailedError
from common.services.job_claim import claim_job
from common.services.transcription_services.transcription_manager import TranscriptionServiceManager
from common.settings import get_structured_logger
from common.workflows import transcription as wf
from common.workflows.activities import _shared

slogger = get_structured_logger()
transcription_manager = TranscriptionServiceManager()


async def _keep_alive() -> None:
    """Heartbeat while the STT call blocks on the provider. This is a liveness signal, not progress:
    the server only sees it (throttled to ~0.8x the heartbeat timeout), but it lets an abrupt worker
    death be noticed in heartbeat_timeout instead of at the end of the much longer start_to_close.
    """
    while True:
        activity.heartbeat()
        await asyncio.sleep(15)


async def _transcribe(params: wf.TranscribeInput) -> str:
    transcription = _shared.load(UUID(params.minute_id))
    if transcription.dialogue_entries or transcription.status == JobStatus.COMPLETED:
        return str(transcription.id)  # a previous attempt already transcribed: idempotent retry
    if transcription.status == JobStatus.FAILED:
        msg = f"Transcription is FAILED: {transcription.error}"
        raise TranscriptionFailedError(msg)
    # claim_job is the status-guarded transition (AWAITING_START -> IN_PROGRESS); an IN_PROGRESS row
    # is this workflow's own earlier attempt, so nothing else is needed to "own" it.
    claim_job(Transcription, transcription.id)
    heartbeat = asyncio.create_task(_keep_alive())
    try:
        # Downloads the newest recording (the mono mp3 prepare_audio saved) and runs one STT call
        # within the workflow's duration-based budget.
        transcription_job = await transcription_manager.perform_transcription_steps(
            transcription=transcription, timeout_seconds=params.stt_timeout_seconds
        )
    except Exception as e:
        if is_transient(e):
            raise _shared.TranscriptionTransientError(str(e)) from e
        if (msg := _shared.mark_failed(transcription, e)) is None:
            raise _shared.TranscriptionTransientError(str(e)) from e
        raise TranscriptionFailedError(msg) from e
    finally:
        heartbeat.cancel()
        with suppress(asyncio.CancelledError):
            await heartbeat
    transcript = transcription_job.transcript
    if not transcript:
        # An async provider (AWS) returns a job to poll; this Temporal path only supports sync providers.
        msg = "Transcription provider did not return a transcript"
        raise _shared.TranscriptionTransientError(msg)
    if not _shared.update_in_progress(transcription.id, dialogue_entries=transcript):
        msg = "Transcription changed while being written"
        raise _shared.TranscriptionTransientError(msg)
    return str(transcription.id)


@activity.defn(name=wf.TRANSCRIBE)
async def transcribe(params: wf.TranscribeInput) -> str:
    """One STT provider call on the prepared mp3. Returns the transcription id."""
    slogger.refresh_context()
    slogger.set_context_field("minute_id", params.minute_id)
    try:
        return await _transcribe(params)
    except _shared.TranscriptionTransientError as e:
        raise ApplicationError(str(e)) from e  # provider unavailable or row moved on: retry with backoff
    except TranscriptionFailedError as e:
        raise ApplicationError(str(e), non_retryable=True) from e  # row is already FAILED, or bad audio

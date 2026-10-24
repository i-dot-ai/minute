"""Activity: one STT call on the prepared mp3, saving the raw transcript."""

from uuid import UUID

from temporalio import activity
from temporalio.exceptions import ApplicationError

from common.database.postgres_models import JobStatus, Transcription
from common.services.exceptions import TranscriptionFailedError
from common.services.job_claim import JobClaimRenewer
from common.services.transcription_services.transcription_manager import TranscriptionServiceManager
from common.settings import get_structured_logger
from common.workflows import transcription as wf
from common.workflows.activities import _shared

slogger = get_structured_logger()
transcription_manager = TranscriptionServiceManager()


async def _transcribe(params: wf.TranscribeInput) -> str:
    transcription = _shared.load(UUID(params.minute_id))
    if transcription.dialogue_entries or transcription.status == JobStatus.COMPLETED:
        return str(transcription.id)  # a previous attempt already transcribed: idempotent retry
    if transcription.status == JobStatus.FAILED:
        msg = f"Transcription is FAILED: {transcription.error}"
        raise TranscriptionFailedError(msg)
    claim = _shared.take_claim(transcription)
    renewer = JobClaimRenewer(Transcription, transcription.id, claim)
    try:
        async with renewer:
            # Downloads the newest recording (the mono mp3 prepare_audio saved) and runs one STT call.
            transcription_job = await transcription_manager.perform_transcription_steps(transcription=transcription)
    except Exception as e:
        if (msg := _shared.mark_failed(transcription, renewer.token, e)) is None:
            raise _shared.TranscriptionTransientError(str(e)) from e
        raise TranscriptionFailedError(msg) from e
    transcript = transcription_job.transcript
    if not transcript:
        # An async provider (AWS) returns a job to poll; this Temporal path only supports sync providers.
        msg = "Transcription provider did not return a transcript"
        raise _shared.TranscriptionTransientError(msg)
    if not _shared.fenced_update(transcription.id, renewer.token, transcript=transcript):
        msg = "Transcription claim was superseded"
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
        raise ApplicationError(str(e)) from e  # provider unavailable or claim moved: retry with backoff
    except TranscriptionFailedError as e:
        raise ApplicationError(str(e), non_retryable=True) from e  # row is already FAILED, or bad audio

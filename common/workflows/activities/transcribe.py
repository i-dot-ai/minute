"""Activity: one Azure STT request on the prepared mp3, saving the raw transcript."""

import tempfile
from pathlib import Path
from uuid import UUID

from temporalio import activity
from temporalio.exceptions import ApplicationError

from common.audio.prepare_audio import prepare_audio as prepare_recording
from common.database.postgres_models import Transcription
from common.runtime import Runtime
from common.services.job_claim import JobClaimRenewer
from common.services.stt import TranscriptionFailedError, TranscriptionTransientError
from common.settings import get_structured_logger
from common.types import JobStatus
from common.workflows import transcription as wf
from common.workflows.activities import _shared

slogger = get_structured_logger()


async def _transcribe(params: wf.TranscribeInput, attempt: int, runtime: Runtime) -> str:
    transcription = await _shared.load(UUID(params.minute_id))
    if transcription.dialogue_entries or transcription.status == JobStatus.COMPLETED:
        return str(transcription.id)  # a previous attempt already transcribed: idempotent retry
    if transcription.status == JobStatus.FAILED:
        msg = f"Transcription is FAILED: {transcription.error}"
        raise TranscriptionFailedError(msg)
    claim = _shared.take_claim(transcription)
    renewer = JobClaimRenewer(Transcription, transcription.id, claim)
    try:
        async with renewer:
            with tempfile.TemporaryDirectory() as work_dir:
                audio = await prepare_recording(
                    transcription, Path(work_dir), runtime.storage, runtime.db
                )  # already a mono mp3: download only
                transcript = await runtime.stt.transcribe(
                    audio.file_path, timeout_seconds=params.stt_timeout_seconds, attempt=attempt
                )
    except TranscriptionTransientError:
        raise  # provider unavailable: row untouched, retry (on the next region)
    except Exception as e:
        if (msg := await _shared.mark_failed(transcription, renewer.token, e)) is None:
            raise TranscriptionTransientError(str(e)) from e
        raise TranscriptionFailedError(msg) from e
    if not await _shared.fenced_update(transcription.id, renewer.token, dialogue_entries=transcript):
        msg = "Transcription claim was superseded"
        raise TranscriptionTransientError(msg)
    return str(transcription.id)


def build_transcribe(runtime: Runtime):
    """Bind the activity to a Runtime so it uses that runtime's storage/stt/db, not globals."""

    @activity.defn(name=wf.TRANSCRIBE)
    async def transcribe(params: wf.TranscribeInput) -> str:
        """One Azure request on the prepared mp3. Returns the transcription id.

        The attempt number (1-based) picks the region, so Temporal's retries walk the regions.
        """
        slogger.refresh_context()
        slogger.set_context_field("minute_id", params.minute_id)
        try:
            return await _transcribe(params, attempt=activity.info().attempt, runtime=runtime)
        except TranscriptionTransientError as e:
            raise ApplicationError(str(e)) from e  # provider unavailable: retry with backoff
        except TranscriptionFailedError as e:
            raise ApplicationError(str(e), non_retryable=True) from e  # row is already FAILED, or bad audio

    return transcribe

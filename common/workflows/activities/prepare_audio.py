"""Activity: claim the transcription and prepare its audio (download, convert to a mono mp3)."""

import tempfile
from pathlib import Path
from uuid import UUID

from temporalio import activity
from temporalio.exceptions import ApplicationError

from common.audio.prepare_audio import prepare_audio as prepare_recording
from common.runtime import Runtime
from common.services.stt import TranscriptionFailedError, TranscriptionTransientError
from common.settings import get_structured_logger
from common.types import JobStatus
from common.workflows import transcription as wf
from common.workflows.activities import _shared

slogger = get_structured_logger()


async def _prepare_audio(minute_id: UUID, runtime: Runtime) -> wf.PreparedAudio:
    transcription = await _shared.load(minute_id)
    if transcription.status not in (JobStatus.AWAITING_START, JobStatus.IN_PROGRESS):
        msg = f"Transcription is {transcription.status}"
        raise TranscriptionFailedError(msg)
    claim = _shared.take_claim(transcription)
    try:
        with tempfile.TemporaryDirectory() as work_dir:
            audio = await prepare_recording(transcription, Path(work_dir), runtime.storage, runtime.db)
    except Exception as e:
        if (msg := await _shared.mark_failed(transcription, claim, e)) is None:
            raise TranscriptionTransientError(str(e)) from e
        raise TranscriptionFailedError(msg) from e
    return wf.PreparedAudio(duration_seconds=audio.duration_seconds)


def build_prepare_audio(runtime: Runtime):
    """Bind the activity to a Runtime so it uses that runtime's storage/db, not a global."""

    @activity.defn(name=wf.PREPARE_AUDIO)
    async def prepare_audio(minute_id: str) -> wf.PreparedAudio:
        """Convert the upload to a mono mp3 and report its duration, so the workflow sizes the STT timeout."""
        slogger.refresh_context()
        try:
            return await _prepare_audio(UUID(minute_id), runtime)
        except TranscriptionTransientError as e:
            raise ApplicationError(str(e)) from e  # claim moved under us: retry
        except TranscriptionFailedError as e:
            raise ApplicationError(str(e), non_retryable=True) from e  # corrupt/missing audio, or already terminal

    return prepare_audio

"""Activity: start the transcription and prepare its audio (download, convert to a mono mp3)."""

import tempfile
from pathlib import Path
from uuid import UUID

from temporalio import activity
from temporalio.exceptions import ApplicationError

from common.database.postgres_models import JobStatus, Transcription
from common.services.errors import is_transient
from common.services.exceptions import TranscriptionFailedError
from common.services.job_claim import claim_job
from common.services.storage_services import get_storage_service
from common.services.transcription_services.transcription_manager import TranscriptionServiceManager
from common.settings import get_settings, get_structured_logger
from common.workflows import transcription as wf
from common.workflows.activities import _shared

slogger = get_structured_logger()
storage_service = get_storage_service(get_settings().STORAGE_SERVICE_NAME)
transcription_manager = TranscriptionServiceManager()


async def _prepare_audio(minute_id: UUID) -> wf.PreparedAudio:
    transcription = _shared.load(minute_id)
    if transcription.status not in (JobStatus.AWAITING_START, JobStatus.IN_PROGRESS):
        msg = f"Transcription is {transcription.status}"
        raise TranscriptionFailedError(msg)
    # claim_job is the status-guarded transition (AWAITING_START -> IN_PROGRESS); an IN_PROGRESS row
    # is this workflow's own earlier attempt, so nothing else is needed to "own" it.
    claim_job(Transcription, transcription.id)
    try:
        with tempfile.TemporaryDirectory() as work_dir:
            recording = transcription.recordings[0]
            temp_file_path = Path(work_dir) / Path(recording.s3_file_key).name
            await storage_service.download(recording.s3_file_key, temp_file_path)
            # Uploads the converted copy and records it, so the transcribe step (a separate
            # attempt/process) can pick the newest recording and skip conversion.
            # ponytail: on retry the newest recording is the converted mp3, so conversion is skipped;
            # two overlapping attempts (activity timeout + retry) can still insert a duplicate copy.
            # Add a (transcription_id, kind) unique index if that shows up.
            _, _, duration = await transcription_manager.get_recording_to_process(
                recording=recording,
                temp_file_path=temp_file_path,
                file_extension=Path(recording.s3_file_key).suffix.lower(),
            )
    except Exception as e:
        if is_transient(e):
            raise _shared.TranscriptionTransientError(str(e)) from e
        if (msg := _shared.mark_failed(transcription, e)) is None:
            raise _shared.TranscriptionTransientError(str(e)) from e
        raise TranscriptionFailedError(msg) from e
    return wf.PreparedAudio(duration_seconds=duration)


@activity.defn(name=wf.PREPARE_AUDIO)
async def prepare_audio(minute_id: str) -> wf.PreparedAudio:
    """Convert the upload to a mono mp3 and report its duration, so the workflow sizes the STT timeout."""
    slogger.refresh_context()
    try:
        return await _prepare_audio(UUID(minute_id))
    except _shared.TranscriptionTransientError as e:
        raise ApplicationError(str(e)) from e  # row moved on or dependency blip: retry
    except TranscriptionFailedError as e:
        raise ApplicationError(str(e), non_retryable=True) from e  # corrupt/missing audio, or already terminal

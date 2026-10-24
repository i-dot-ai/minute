"""Activity: mark the transcription FAILED once its retries are exhausted, so the user can retry."""

from uuid import UUID

from temporalio import activity

from common.database.postgres_models import JobStatus
from common.services.exceptions import TranscriptionFailedError
from common.services.posthog_client import capture_event
from common.workflows import transcription as wf
from common.workflows.activities import _shared


@activity.defn(name=wf.FAIL_TRANSCRIPTION)
async def fail_transcription(params: wf.FailTranscriptionInput) -> None:
    """IN_PROGRESS -> FAILED. No-op if the row is already terminal or was deleted."""
    try:
        transcription = _shared.load(UUID(params.minute_id))
    except TranscriptionFailedError:
        return  # deleted
    error = f"Transcription failed: {params.error}"
    if _shared.update_in_progress(transcription.id, status=JobStatus.FAILED, error=error):
        capture_event(transcription.user_id, "transcription_failed", {"transcriptionId": str(transcription.id)})

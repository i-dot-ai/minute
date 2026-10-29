"""Activity: mark the transcription FAILED once its retries are exhausted, so the user can retry."""

from uuid import UUID

from temporalio import activity

from common.services.exceptions import TranscriptionFailedError
from common.workflows import transcription as wf
from common.workflows.activities import _shared


@activity.defn(name=wf.FAIL_TRANSCRIPTION)
async def fail_transcription(params: wf.FailTranscriptionInput) -> None:
    """Finalise unfinished work. No-op if the row is already terminal or was deleted."""
    try:
        transcription = _shared.load(UUID(params.minute_id))
    except TranscriptionFailedError:
        return  # deleted
    _shared.mark_failed(transcription, params.error)

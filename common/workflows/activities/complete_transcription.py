"""Activity: mark the transcription COMPLETED (the transcript is now usable)."""

from uuid import UUID

from temporalio import activity

from common.database.postgres_models import JobStatus
from common.services.posthog_client import capture_event
from common.workflows import transcription as wf
from common.workflows.activities import _shared


@activity.defn(name=wf.COMPLETE_TRANSCRIPTION)
async def complete_transcription(transcription_id: str) -> bool:
    """IN_PROGRESS -> COMPLETED. Idempotent: True if already COMPLETED, False if deleted or failed."""
    tid = UUID(transcription_id)
    if _shared.update_in_progress(tid, status=JobStatus.COMPLETED):
        row = _shared.get_row(tid)
        if row:
            capture_event(row.user_id, "transcription_succeeded", {"transcriptionId": transcription_id})
        return True
    row = _shared.get_row(tid)
    return row is not None and row.status == JobStatus.COMPLETED

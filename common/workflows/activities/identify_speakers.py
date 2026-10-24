"""Activity: name the speakers in the transcript (one LLM call; failures degrade)."""

from uuid import UUID

from temporalio import activity

from common.services.transcription_handler_service import TranscriptionHandlerService
from common.workflows import transcription as wf
from common.workflows.activities import _shared


@activity.defn(name=wf.IDENTIFY_SPEAKERS)
async def identify_speakers(transcription_id: str) -> None:
    transcription_id_uuid = UUID(transcription_id)
    row = _shared.in_progress(transcription_id_uuid)
    if row is None or not row.dialogue_entries:
        return
    # ponytail: no separate raw transcript column, so a retry after a successful write
    # re-labels already-named entries; store raw.json in S3 to make this pure.
    named = await TranscriptionHandlerService.identify_speakers(row.dialogue_entries)
    _shared.update_in_progress(transcription_id_uuid, dialogue_entries=named)

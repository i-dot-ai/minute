"""Activity: generate a title for the transcription (one LLM call; failures degrade)."""

from uuid import UUID

from temporalio import activity

from common.generate_meeting_title import generate_meeting_title
from common.workflows import transcription as wf
from common.workflows.activities import _shared


@activity.defn(name=wf.GENERATE_TITLE)
async def generate_title(transcription_id: str) -> None:
    transcription_id_uuid = UUID(transcription_id)
    row = await _shared.in_progress(transcription_id_uuid)
    if row is None or not row.dialogue_entries:
        return
    title = await generate_meeting_title(transcript=row.dialogue_entries)
    if title:
        await _shared.update_in_progress(transcription_id_uuid, title=title)

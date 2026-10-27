"""Activity: generate a title for the transcription (one LLM call; failures degrade)."""

from uuid import UUID

from temporalio import activity

from common.generate_meeting_title import generate_meeting_title
from common.workflows import transcription as wf
from common.workflows.activities import _shared


@activity.defn(name=wf.GENERATE_TITLE)
async def generate_title(transcription_id: str) -> None:
    transcription_id_uuid = UUID(transcription_id)
    row = _shared.in_progress(transcription_id_uuid)
    if row is None or not row.dialogue_entries or row.title:
        return
    # generate_meeting_title raises on LLM failure; the activity retries, and the workflow treats a
    # missing title as optional.
    title = await generate_meeting_title(transcript=row.dialogue_entries)
    if title:
        _shared.set_title_if_empty(transcription_id_uuid, title)

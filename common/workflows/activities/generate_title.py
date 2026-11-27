"""Activity: generate a title and search keywords in one optional LLM call."""

from uuid import UUID

from temporalio import activity

from common.generate_meeting_title import generate_meeting_title
from common.workflows import transcription as wf
from common.workflows.activities import _shared


@activity.defn(name=wf.GENERATE_TITLE)
async def generate_title(transcription_id: str) -> None:
    transcription_id_uuid = UUID(transcription_id)
    row = _shared.in_progress(transcription_id_uuid)
    if row is None or not row.dialogue_entries:
        return
    if row.title and row.search_keywords is not None:
        return
    metadata = await generate_meeting_title(transcript=row.dialogue_entries)
    _shared.set_generated_title_and_keywords(row, metadata.title.strip(), metadata.keywords)

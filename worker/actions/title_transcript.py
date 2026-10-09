"""Action: generate a short meeting title from the transcript."""

from pydantic import BaseModel, Field

from common.database.postgres_models import DialogueEntry
from common.settings import get_structured_logger
from worker.llm import FastOrBestLLM, create_default_chatbot
from worker.text import transcript_as_speaker_and_utterance

slogger = get_structured_logger()


class MeetingTitleResponse(BaseModel):
    title: str = Field(description="A short title for the meeting")


def _title_prompt(transcript: list[DialogueEntry]) -> list[dict[str, str]]:
    prompt = f"""<task>
Generate a short title for the meeting
</task>

<transcript>
{transcript_as_speaker_and_utterance(transcript)}
</transcript>"""
    return [{"role": "user", "content": prompt}]


async def generate_meeting_title(transcript: list[DialogueEntry]) -> str:
    try:
        chatbot = create_default_chatbot(fast_or_best=FastOrBestLLM.FAST)
        response = await chatbot.structured_chat(
            messages=_title_prompt(transcript=transcript), response_format=MeetingTitleResponse
        )
        return response.title
    except Exception:  # noqa: BLE001 - title is cosmetic, never fail the job over it
        slogger.warning("Meeting title generation failed, continuing without title")
        return ""

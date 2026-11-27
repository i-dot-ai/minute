from pydantic import BaseModel, Field

from common.database.postgres_models import DialogueEntry
from common.llm.client import ModelTier, get_chatbot
from common.prompts import get_meeting_title_prompt


class MeetingTitleResponse(BaseModel):
    title: str = Field(description="A short title for the meeting")


async def generate_meeting_title(transcript: list[DialogueEntry]) -> str:
    """Raises on LLM failure; the activity retries and the workflow treats a missing title as optional."""
    chatbot = get_chatbot(ModelTier.LIGHTWEIGHT)
    response = await chatbot.structured_chat(
        messages=get_meeting_title_prompt(transcript=transcript), response_format=MeetingTitleResponse
    )
    return response.title

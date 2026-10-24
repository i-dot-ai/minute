from pydantic import BaseModel, Field

from common.database.postgres_models import DialogueEntry
from common.llm.client import FastOrBestLLM, create_default_chatbot
from common.prompts import get_meeting_title_prompt


class MeetingTitleResponse(BaseModel):
    title: str = Field(description="A short title for the meeting")


async def generate_meeting_title(transcript: list[DialogueEntry]) -> str:
    try:
        chatbot = create_default_chatbot(fast_or_best=FastOrBestLLM.FAST)
        response = await chatbot.structured_chat(
            messages=get_meeting_title_prompt(transcript=transcript), response_format=MeetingTitleResponse
        )
        return response.title
    except:  # noqa: E722
        return ""

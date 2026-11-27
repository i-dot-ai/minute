from pydantic import BaseModel, Field, TypeAdapter, ValidationError, field_validator

from common.database.postgres_models import DialogueEntry
from common.llm.client import FastOrBestLLM, create_default_chatbot
from common.prompts import get_meeting_title_prompt
from common.types import TranscriptionKeyword, deduplicate_keywords

_keyword_adapter = TypeAdapter(TranscriptionKeyword)


class MeetingTitleResponse(BaseModel):
    title: str = Field(description="A short title for the meeting")
    keywords: list[str] = Field(description="Short search terms or phrases")

    @field_validator("keywords")
    @classmethod
    def normalize_keywords(cls, keywords: list[str]) -> list[str]:
        # Azure OpenAI's structured output schema does not support length constraints.
        valid = []
        for keyword in keywords:
            try:
                valid.append(_keyword_adapter.validate_python(keyword))
            except ValidationError:
                continue
        return deduplicate_keywords(valid)


async def generate_meeting_title(transcript: list[DialogueEntry]) -> MeetingTitleResponse:
    """Generate the title and keywords in one call; the activity retries provider failures."""
    chatbot = create_default_chatbot(fast_or_best=FastOrBestLLM.FAST)
    return await chatbot.structured_chat(
        messages=get_meeting_title_prompt(transcript=transcript), response_format=MeetingTitleResponse
    )

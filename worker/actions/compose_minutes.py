"""Action: classify the meeting and generate the minute HTML (template dispatch + LLM)."""

import re
from typing import cast

import mistune
from sqlalchemy.orm import selectinload
from sqlmodel.ext.asyncio.session import AsyncSession

from common.database.postgres_database import async_engine
from common.database.postgres_models import DialogueEntry, Minute, UserTemplate
from common.settings import get_settings, get_structured_logger
from common.spelling import convert_american_to_british_spelling
from common.types import MeetingType
from worker.llm import FastOrBestLLM, create_default_chatbot
from worker.templates import get_template
from worker.templates.prompts import get_transcript_messages
from worker.templates.user_template import generate_user_template
from worker.text import transcript_as_speaker_and_utterance

slogger = get_structured_logger()
settings = get_settings()

fenced_document_pattern = re.compile(r"\A\s*```[a-zA-Z]*\n(.*?)\n?```\s*\Z", re.DOTALL)


def strip_document_code_fence(markdown: str) -> str:
    """Unwrap a whole minute that the model returned inside a code fence.

    mistune turns a fence around the entire document into a single <pre><code> block, which renders
    the minute as raw Markdown rather than as formatted text.
    """
    match = fenced_document_pattern.match(markdown)
    return match.group(1) if match else markdown


def classify_meeting(dialogue_entries: list[DialogueEntry]) -> MeetingType:
    word_count = sum(len(entry["text"].split()) for entry in dialogue_entries)
    match word_count:
        case n if n < settings.MIN_WORD_COUNT_FOR_SUMMARY:
            return MeetingType.too_short
        case n if n < settings.MIN_WORD_COUNT_FOR_FULL_SUMMARY:
            return MeetingType.short
        case _:
            return MeetingType.standard


def _bad_transcript_minutes(transcript: list[DialogueEntry]) -> str:
    return f"""Short meeting detected. Minutes not available.
         Please try again with a longer meeting. Transcript is: {transcript_as_speaker_and_utterance(transcript)}"""


async def _basic_minutes(transcript: list[DialogueEntry]) -> str:
    chatbot = create_default_chatbot(FastOrBestLLM.FAST)
    return await chatbot.chat(
        [
            {"role": "system", "content": "Provide a simple summary of the meeting."},
            get_transcript_messages(transcript),
        ]
    )


async def _full_minutes(minute: Minute) -> str:
    if minute.user_template_id is not None:
        async with AsyncSession(async_engine) as session:
            template = await session.get(
                UserTemplate,
                minute.user_template_id,
                options=[selectinload(UserTemplate.questions)],  # pyright: ignore[reportArgumentType]
            )
        if not template:
            msg = f"No template with id {minute.user_template_id}"
            raise RuntimeError(msg)
        result = await generate_user_template(template=template, transcription=minute.transcription)
    else:
        template = get_template(minute.template_name)
        result = await template.generate(minute)
    return convert_american_to_british_spelling(result)


async def compose_minutes(minute: Minute) -> str:
    """Generate the minute's HTML content for a minute whose transcription is complete."""
    transcript = minute.transcription.dialogue_entries or []
    match classify_meeting(transcript):
        case MeetingType.too_short:
            slogger.info("Transcript too short for minute generation, writing fallback")
            result = _bad_transcript_minutes(transcript)
        case MeetingType.short:
            slogger.info("Short transcript, generating basic minutes")
            result = await _basic_minutes(transcript)
        case _:
            slogger.info(
                "Generating full minutes with template={template} meeting_type={meeting_type}",
                template=minute.template_name,
                meeting_type=MeetingType.standard,
            )
            result = await _full_minutes(minute)
    return cast(str, mistune.html(strip_document_code_fence(result)))

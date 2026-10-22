import logging
import re
from datetime import datetime
from enum import StrEnum, auto
from typing import cast
from uuid import UUID

import mistune
from sqlalchemy import update
from sqlmodel import col

from common.database.postgres_database import AsyncSessionLocal
from common.database.postgres_models import Minute, MinuteVersion
from common.database.repository import (
    get_only_version_for_minute,
    get_user_template_with_questions,
    get_version_with_transcription,
)
from common.format_transcript import transcript_as_speaker_and_utterance
from common.llm.client import FastOrBestLLM, create_default_chatbot
from common.prompts import (
    get_ai_edit_initial_messages,
    get_basic_minutes_prompt,
)
from common.services.job_claim import JobClaimRenewer, claim_job
from common.services.posthog_client import capture_event
from common.services.template_manager import TemplateManager
from common.settings import get_settings, get_structured_logger
from common.spelling import convert_american_to_british_spelling
from common.templates.user_template import generate_user_template
from common.types import DialogueEntry, JobStatus, MeetingType

settings = get_settings()

logger = logging.getLogger(__name__)
slogger = get_structured_logger()


class MinuteGenerationFailedError(Exception):
    pass


class MinuteDelivery(StrEnum):
    ACK = auto()
    LEAVE = auto()


fenced_document_pattern = re.compile(r"\A\s*```[a-zA-Z]*\n(.*?)\n?```\s*\Z", re.DOTALL)


def strip_document_code_fence(markdown: str) -> str:
    """Unwrap a whole minute that the model returned inside a code fence.

    mistune turns a fence around the entire document into a single <pre><code> block, which renders
    the minute as raw Markdown rather than as formatted text.
    """
    match = fenced_document_pattern.match(markdown)
    return match.group(1) if match else markdown


class MinuteHandlerService:
    @staticmethod
    def claim_minute_version(minute_version_id: UUID) -> datetime | None:
        return claim_job(MinuteVersion, minute_version_id)

    @staticmethod
    async def update_minute_version(
        minute_version_id: UUID,
        claim_token: datetime,
        html_content: str | None = None,
        status: JobStatus | None = None,
        error: str | None = None,
    ) -> bool:
        """Update a minute version only while claim_token still owns it.

        The update is applied only if the row still carries the claim token, so a
        superseded worker's late write is dropped instead of clobbering the new owner.
        Returns whether the write was applied. Claim-specific, so it stays here rather
        than in the repository.
        """
        values: dict = {}
        if html_content is not None:
            values["html_content"] = html_content
        if status is not None:
            values["status"] = status
        if error is not None:
            values["error"] = error
        async with AsyncSessionLocal() as session:
            result = await session.exec(
                update(MinuteVersion)
                .where(
                    col(MinuteVersion.id) == minute_version_id,
                    col(MinuteVersion.updated_datetime) == claim_token,
                )
                .values(**values)
            )
            await session.commit()
            return result.rowcount == 1  # pyright: ignore[reportAttributeAccessIssue]

    @classmethod
    async def record_minute_version_failure(cls, minute_version_id: UUID, error: str, claim_token: datetime) -> bool:
        return await cls.update_minute_version(
            minute_version_id, status=JobStatus.FAILED, error=error, claim_token=claim_token
        )

    @classmethod
    async def get_minute_version(cls, minute_version_id: UUID) -> MinuteVersion:
        async with AsyncSessionLocal() as session:
            return await get_version_with_transcription(session, minute_version_id)

    @classmethod
    async def get_only_minute_version_for_minute_id(cls, minute_id: UUID) -> MinuteVersion:
        async with AsyncSessionLocal() as session:
            return await get_only_version_for_minute(session, minute_id)

    @classmethod
    async def process_minute_generation_message(cls, minute_version_id: UUID) -> MinuteDelivery:
        try:
            minute_version = await cls.get_minute_version(minute_version_id=minute_version_id)
            slogger.set_context_field("minute_id", str(minute_version.minute_id))
            slogger.set_context_field("user_id", str(minute_version.minute.transcription.user_id))
            slogger.info("Successfully found MinuteVersion")
        except Exception as e:
            raise MinuteGenerationFailedError from e
        token = cls.claim_minute_version(minute_version.id)
        if token is None:
            current = await cls.get_minute_version(minute_version.id)
            if current.status in (JobStatus.COMPLETED, JobStatus.FAILED):
                return MinuteDelivery.ACK
            return MinuteDelivery.LEAVE
        renewer = JobClaimRenewer(MinuteVersion, minute_version.id, token)
        try:
            async with renewer:
                meeting_type = cls.predict_meeting(minute_version.minute.transcription.dialogue_entries)
                slogger.info("Predicted meeting type {meeting_type}", meeting_type=str(meeting_type))
                html_content = await cls.generate_minutes(meeting_type, minute_version.minute)
            if not await cls.update_minute_version(
                minute_version.id,
                html_content=html_content,
                status=JobStatus.COMPLETED,
                claim_token=renewer.token,
            ):
                return MinuteDelivery.ACK
            capture_event(
                minute_version.minute.transcription.user_id,
                "summary_generation_succeeded",
                {"transcriptionId": str(minute_version.minute.transcription_id)},
            )
        except Exception as e:
            if not await cls.record_minute_version_failure(minute_version.id, error=str(e), claim_token=renewer.token):
                return MinuteDelivery.ACK
            capture_event(
                minute_version.minute.transcription.user_id,
                "summary_generation_failed",
                {"transcriptionId": str(minute_version.minute.transcription_id)},
            )
            raise MinuteGenerationFailedError from e
        return MinuteDelivery.ACK

    @classmethod
    async def process_minute_edit_message(
        cls, source_minute_version_id: UUID, target_minute_version_id: UUID
    ) -> MinuteDelivery:
        try:
            target_minute_version = await cls.get_minute_version(target_minute_version_id)
            slogger.set_context_field("minute_id", str(target_minute_version.minute_id))
            slogger.set_context_field("user_id", str(target_minute_version.minute.transcription.user_id))
        except Exception as e:
            raise MinuteGenerationFailedError from e

        token = cls.claim_minute_version(target_minute_version.id)
        if token is None:
            current = await cls.get_minute_version(target_minute_version.id)
            if current.status in (JobStatus.COMPLETED, JobStatus.FAILED):
                return MinuteDelivery.ACK
            return MinuteDelivery.LEAVE
        renewer = JobClaimRenewer(MinuteVersion, target_minute_version.id, token)
        try:
            async with renewer:
                source_minute_version = await cls.get_minute_version(source_minute_version_id)
                if (
                    not source_minute_version.minute.transcription.user_id
                    or source_minute_version.minute.transcription.user_id
                    != target_minute_version.minute.transcription.user_id
                ):
                    msg = "Source and target minute versions belong to different users"
                    raise ValueError(msg)
                if not str(target_minute_version.ai_edit_instructions or "").strip():
                    msg = "Target minute does not have AI edit instructions"
                    raise ValueError(msg)
                edited_string = await cls.edit_minutes_with_ai(
                    minutes=source_minute_version.html_content,
                    edit_instructions=target_minute_version.ai_edit_instructions,
                    transcript=source_minute_version.minute.transcription.dialogue_entries,
                )
            await cls.update_minute_version(
                minute_version_id=target_minute_version.id,
                status=JobStatus.COMPLETED,
                html_content=edited_string,
                claim_token=renewer.token,
            )
            return MinuteDelivery.ACK
        except Exception as e:
            if not await cls.record_minute_version_failure(
                target_minute_version.id, error=str(e), claim_token=renewer.token
            ):
                return MinuteDelivery.ACK
            raise MinuteGenerationFailedError from e

    @classmethod
    async def generate_minute_from_user_template(cls, minute: Minute):
        if minute.user_template_id is None:
            msg = "Minute has no user template"
            raise RuntimeError(msg)
        async with AsyncSessionLocal() as session:
            template = await get_user_template_with_questions(session, minute.user_template_id)
        if not template:
            msg = f"No template with id {minute.user_template_id}"
            raise RuntimeError(msg)
        logger.info("%s: Found template id=%s, name=%s", minute.id, template.id, template.name)
        return await generate_user_template(template=template, transcription=minute.transcription)

    @classmethod
    async def generate_minutes(
        cls,
        meeting_type: MeetingType,
        minute: Minute,
    ) -> str:
        match meeting_type:
            case MeetingType.too_short:
                result = cls.handle_bad_transcript(minute.transcription.dialogue_entries)
            case MeetingType.short:
                result = await cls.generate_basic_minutes(minute.transcription.dialogue_entries)
            case _:
                result = await cls.generate_full_minutes(minute)
        result = mistune.html(strip_document_code_fence(result))
        return cast(str, result)

    @classmethod
    async def generate_full_minutes(cls, minute: Minute) -> str:
        if minute.user_template_id is not None:
            logger.info(
                "%s: Generating minute from user template user_template_id=%s", minute.id, minute.user_template_id
            )
            result = await cls.generate_minute_from_user_template(minute)
        else:
            logger.info("%s: Generating minute from default template: %s", minute.id, minute.template_name)
            template = TemplateManager.get_template(minute.template_name)
            result = await template.generate(minute)
        logger.info("%s: Successfully generated minute", minute.id)
        return convert_american_to_british_spelling(result)

    @classmethod
    def handle_bad_transcript(cls, transcript: list[DialogueEntry]) -> str:
        return f"""Short meeting detected. Minutes not available.
         Please try again with a longer meeting. Transcript is: {transcript_as_speaker_and_utterance(transcript)}"""

    @classmethod
    async def generate_basic_minutes(
        cls,
        transcript: list[DialogueEntry],
    ) -> str:
        chatbot = create_default_chatbot(FastOrBestLLM.FAST)
        return await chatbot.chat(messages=get_basic_minutes_prompt(transcript))

    @classmethod
    def predict_meeting(cls, dialogue_entries: list[DialogueEntry]) -> MeetingType:
        word_count = sum(len(entry["text"].split()) for entry in dialogue_entries)
        match word_count:
            case n if n < settings.MIN_WORD_COUNT_FOR_SUMMARY:
                return MeetingType.too_short
            case n if n < settings.MIN_WORD_COUNT_FOR_FULL_SUMMARY:
                return MeetingType.short
            case _:
                return MeetingType.standard

    @classmethod
    async def edit_minutes_with_ai(
        cls,
        minutes: str,
        edit_instructions: str,
        transcript: list[DialogueEntry],
    ) -> str:
        chatbot = create_default_chatbot(FastOrBestLLM.FAST)
        edited_minutes = await chatbot.chat(
            messages=get_ai_edit_initial_messages(minutes, edit_instructions, transcript)
        )
        return edited_minutes.removeprefix("```html").removesuffix("```")

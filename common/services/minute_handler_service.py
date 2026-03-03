import logging
import uuid
from typing import cast
from uuid import UUID

import mistune
from sqlalchemy.orm import selectinload

from common.convert_american_to_british_spelling import convert_american_to_british_spelling
from common.database.postgres_database import SessionLocal
from common.database.postgres_models import DialogueEntry, Hallucination, JobStatus, Minute, MinuteVersion, UserTemplate
from common.format_transcript import transcript_as_speaker_and_utterance
from common.llm.client import FastOrBestLLM, create_default_chatbot
from common.prompts import (
    get_ai_edit_initial_messages,
    get_basic_minutes_prompt,
)
from common.services.template_manager import TemplateManager
from common.settings import get_settings
from common.templates.user_template import generate_user_template
from common.types import (
    LLMHallucination,
    MeetingType,
    MinuteAndHallucinations,
)

settings = get_settings()

logger = logging.getLogger(__name__)


class MinuteGenerationFailedError(Exception):
    pass


class MinuteHandlerService:
    @staticmethod
    def convert_llm_hallucination_to_db_hallucination(
        llm_hallucination: LLMHallucination, minute_version_id: UUID
    ) -> Hallucination:
        return Hallucination(
            id=uuid.uuid4(),
            hallucination_text=llm_hallucination.hallucination_text,
            hallucination_reason=llm_hallucination.hallucination_reason,
            hallucination_type=llm_hallucination.hallucination_type,
            minute_version_id=minute_version_id,
        )

    @staticmethod
    def update_minute_version(
        minute_version_id: UUID,
        html_content: str | None = None,
        status: JobStatus | None = None,
        error: str | None = None,
        hallucinations: list[LLMHallucination] | None = None,
    ) -> None:
        with SessionLocal() as session:
            minute_version = session.get(MinuteVersion, minute_version_id)
            if not minute_version:
                err_msg = f"MinuteVersion not found for id: {minute_version_id}"
                raise ValueError(err_msg)

            if html_content:
                minute_version.html_content = html_content
            if status:
                minute_version.status = status
            if error:
                minute_version.error = error
            if hallucinations:
                minute_version.hallucinations = [
                    MinuteHandlerService.convert_llm_hallucination_to_db_hallucination(hallucination, minute_version_id)
                    for hallucination in hallucinations
                ]
            session.add(minute_version)
            session.commit()

    @classmethod
    async def get_minute_version(cls, minute_version_id: UUID) -> MinuteVersion:
        with SessionLocal() as session:
            minute_version = session.get(
                MinuteVersion,
                minute_version_id,
                options=[selectinload(MinuteVersion.minute).selectinload(Minute.transcription)],
            )
            if not minute_version:
                msg = f"MinuteVersion not found for id: {minute_version_id}"
                raise ValueError(msg)
            session.expunge(minute_version)
            return minute_version

    @classmethod
    async def get_only_minute_version_for_minute_id(cls, minute_id: UUID) -> MinuteVersion:
        with SessionLocal() as session:
            minute = session.get(
                Minute,
                minute_id,
                options=[selectinload(Minute.minute_versions)],
            )
            if not minute:
                msg = f"Minute not found for minute id: {minute_id}"
                raise ValueError(msg)
            if not minute.minute_versions:
                msg = f"MinuteVersion not found for minute id: {minute_id}"
                raise ValueError(msg)
            if len(minute.minute_versions) != 1:
                msg = (
                    f"More than one MinuteVersions found for minute id: {minute_id}. This function should only be "
                    f"used for the initial generation of a Minute."
                )
                raise ValueError(msg)

            session.expunge(minute)
            return minute.minute_versions[0]

    @classmethod
    async def process_minute_generation_message(cls, minute_version_id: UUID) -> None:
        try:
            minute_version = await cls.get_minute_version(minute_version_id=minute_version_id)
            logger.info("%s: Successfully found MinuteVersion", minute_version.minute_id)
        except Exception as e:
            raise MinuteGenerationFailedError from e
        try:
            dialogue_entries = minute_version.minute.transcription.dialogue_entries
            if not dialogue_entries:
                msg = f"Transcription for minute {minute_version.minute_id} has no dialogue entries"
                raise MinuteGenerationFailedError(msg)

            meeting_type = cls.predict_meeting(dialogue_entries)
            logger.info("%s: Predicted minute version %s", minute_version.minute_id, meeting_type)
            html_content, hallucinations = await cls.generate_minutes(meeting_type, minute_version.minute)
            cls.update_minute_version(
                minute_version.id,
                html_content=html_content,
                hallucinations=hallucinations,
                status=JobStatus.COMPLETED,
            )
        except Exception as e:
            cls.update_minute_version(minute_version.id, status=JobStatus.FAILED, error=str(e))
            raise MinuteGenerationFailedError from e

    @classmethod
    async def process_minute_edit_message(cls, source_minute_version_id: UUID, target_minute_version_id: UUID) -> None:
        try:
            source_minute_version = await cls.get_minute_version(source_minute_version_id)
            target_minute_version = await cls.get_minute_version(target_minute_version_id)
        except Exception as e:
            raise MinuteGenerationFailedError from e

        if (
            target_minute_version.ai_edit_instructions is None
            or str(target_minute_version.ai_edit_instructions).strip() == ""
        ):
            msg = "Target minute does not have AI edit instructions"
            raise MinuteGenerationFailedError(msg)

        try:
            transcript = source_minute_version.minute.transcription.dialogue_entries
            if not transcript:
                msg = "Source minute version has no transcript"
                raise MinuteGenerationFailedError(msg)

            edited_string, hallucinations = await cls.edit_minutes_with_ai(
                minutes=source_minute_version.html_content,
                edit_instructions=target_minute_version.ai_edit_instructions,
                transcript=transcript,
            )
            cls.update_minute_version(
                minute_version_id=target_minute_version.id,
                status=JobStatus.COMPLETED,
                html_content=edited_string,
                hallucinations=hallucinations,
            )

        except Exception as e:
            cls.update_minute_version(target_minute_version.id, status=JobStatus.FAILED, error=str(e))
            raise MinuteGenerationFailedError from e

    @classmethod
    async def generate_minute_from_user_template(cls, minute: Minute) -> MinuteAndHallucinations:
        with SessionLocal() as session:
            template = session.get(
                UserTemplate, minute.user_template_id, options=[selectinload(UserTemplate.questions)]
            )
        if not template:
            msg = f"No template with id {minute.user_template_id}"
            raise RuntimeError(msg)
        logger.info("%s: Found template id=%s, name=%s", minute.id, template.id, template.name)
        minutes, hallucinations = await generate_user_template(template=template, transcription=minute.transcription)
        return minutes, hallucinations

    @classmethod
    async def generate_minutes(
        cls,
        meeting_type: MeetingType,
        minute: Minute,
    ) -> MinuteAndHallucinations:
        dialogue_entries = minute.transcription.dialogue_entries
        if not dialogue_entries:
            msg = f"Minute {minute.id} has no dialogue entries"
            raise MinuteGenerationFailedError(msg)

        result: str
        hallucinations: list[LLMHallucination] | None

        match meeting_type:
            case MeetingType.too_short:
                result, hallucinations = cls.handle_bad_transcript(dialogue_entries)
            case MeetingType.short:
                result, hallucinations = await cls.generate_basic_minutes(dialogue_entries)
            case _:
                result, hallucinations = await cls.generate_full_minutes(minute)
        html_result = mistune.html(result)
        return cast(str, html_result), hallucinations

    @classmethod
    async def generate_full_minutes(cls, minute: Minute) -> MinuteAndHallucinations:
        if minute.user_template_id is not None:
            logger.info(
                "%s: Generating minute from user template user_template_id=%s", minute.id, minute.user_template_id
            )
            result, hallucinations = await cls.generate_minute_from_user_template(minute)
        else:
            logger.info("%s: Generating minute from default template: %s", minute.id, minute.template_name)
            template = TemplateManager.get_template(minute.template_name)
            result, hallucinations = await template.generate(minute)
        logger.info("%s: Successfully generated minute", minute.id)
        result = convert_american_to_british_spelling(result)
        return result, hallucinations

    @classmethod
    def handle_bad_transcript(cls, transcript: list[DialogueEntry]) -> MinuteAndHallucinations:
        return (
            f"""Short meeting detected. Minutes not available.
         Please try again with a longer meeting. Transcript is: {transcript_as_speaker_and_utterance(transcript)}""",
            [],
        )

    @classmethod
    async def generate_basic_minutes(
        cls,
        transcript: list[DialogueEntry],
    ) -> MinuteAndHallucinations:
        chatbot = create_default_chatbot(FastOrBestLLM.FAST)
        choice = await chatbot.chat(messages=get_basic_minutes_prompt(transcript))
        hallucinations = await chatbot.hallucination_check()
        return choice, hallucinations

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
    ) -> MinuteAndHallucinations:
        chatbot = create_default_chatbot(FastOrBestLLM.FAST)
        edited_minutes = await chatbot.chat(
            messages=get_ai_edit_initial_messages(minutes, edit_instructions, transcript)
        )
        edited_minutes = edited_minutes.removeprefix("```html").removesuffix("```")
        hallucinations = await chatbot.hallucination_check()

        return edited_minutes, hallucinations

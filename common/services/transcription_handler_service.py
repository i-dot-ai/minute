from uuid import UUID

from sqlalchemy import update
from sqlalchemy.orm import selectinload
from sqlmodel import col, select

from common.audio.speakers import process_speakers_and_dialogue_entries
from common.database.postgres_database import SessionLocal
from common.database.postgres_models import Chat, JobStatus, Minute, Transcription
from common.generate_meeting_title import generate_meeting_title
from common.llm.client import FastOrBestLLM, create_default_chatbot
from common.prompts import get_chat_with_transcript_system_message
from common.services.exceptions import (
    InteractionFailedError,
    StaleTranscriptionRunError,
    TranscriptionAlreadyStartedError,
    TranscriptionFailedError,
)
from common.services.posthog_client import capture_event
from common.services.transcription_services.transcription_manager import TranscriptionServiceManager
from common.settings import get_settings, get_structured_logger
from common.templates.citations import combine_consecutive_citations
from common.types import DialogueEntry, TranscriptionJobMessageData, TranscriptionReadyMessageData

settings = get_settings()
transcription_manager = TranscriptionServiceManager()
slogger = get_structured_logger()


class TranscriptionHandlerService:
    @classmethod
    def get_transcription(cls, transcription_id: UUID) -> Transcription:
        with SessionLocal() as session:
            transcription = session.exec(
                select(Transcription)
                .where(Transcription.id == transcription_id)
                .options(selectinload(Transcription.recordings))
            ).first()
            if transcription is None:
                msg = f"transcription id {transcription_id} not found"
                raise ValueError(msg)
            if not transcription.recordings:
                msg = f"transcription id {transcription_id} has no recording!"
                raise ValueError(msg)

            session.expunge(transcription)
            return transcription

    @staticmethod
    async def process_interactive_message(chat_id: UUID) -> None:
        """Process an interactive message from the LLM and return the result."""
        slogger.set_context_field("chat_id", str(chat_id))
        try:
            chatbot = create_default_chatbot(FastOrBestLLM.FAST)
            with SessionLocal() as session:
                chat = session.get(Chat, chat_id)

                if not chat:
                    msg = f"Chat id {chat_id} not found"
                    raise InteractionFailedError(msg)

                query = (
                    select(Chat)
                    .where(Chat.transcription_id == chat.transcription_id)
                    .order_by(col(Chat.updated_datetime).asc())
                    .options(selectinload(Chat.transcription))
                )
                result = session.exec(query)
                chats = result.all()

                slogger.set_context_field("user_id", str(chat.transcription.user_id))

                chat_history = [get_chat_with_transcript_system_message(chat.transcription.dialogue_entries)]
                for entry in chats:
                    chat_history.append(
                        {
                            "role": "user",
                            "content": entry.user_content,
                        }
                    )
                    if entry.assistant_content:
                        chat_history.append(
                            {
                                "role": "assistant",
                                "content": entry.assistant_content,
                            }
                        )

                chat_response = await chatbot.chat(messages=chat_history)
                chat_response = combine_consecutive_citations(chat_response)
                chat.assistant_content = chat_response
                chat.status = JobStatus.COMPLETED

                session.add(chat)
                session.commit()
        except Exception as e:
            # Primary failure is logged once at the actor boundary (RayLlmService.process_interactive_task).
            msg = f"Chat interaction failed: {e!s}"
            try:
                chat.status = JobStatus.FAILED
                chat.error = msg
                session.add(chat)
                session.commit()
            except Exception:
                slogger.exception("Error updating chat status. Maybe it doesn't exist?")

            raise InteractionFailedError from e

    @classmethod
    def get_transcription_from_minute_id(cls, minute_id: UUID) -> Transcription:
        with SessionLocal() as session:
            minute = session.get(
                Minute,
                minute_id,
                options=[selectinload(Minute.transcription).selectinload(Transcription.recordings)],
            )
            if not minute:
                msg = f"minute id {minute_id} not found"
                raise ValueError(msg)
            if not minute.transcription:
                msg = f"minute id {minute_id} has no transcription!"
                raise ValueError(msg)

            transcription = minute.transcription
            session.expunge(transcription)
            return transcription

    @classmethod
    def update_transcription(
        cls,
        transcription_id: UUID,
        run_id: UUID | None,
        expected_status: JobStatus,
        status: JobStatus | None = None,
        transcript: list[DialogueEntry] | None = None,
        title: str | None = None,
        error: str | None = None,
    ) -> bool:
        with SessionLocal() as session:
            values = {}
            if status:
                values["status"] = status
            if transcript:
                values["dialogue_entries"] = transcript
            if error:
                values["error"] = error
            if title:
                values["title"] = title
            result = session.exec(
                update(Transcription)
                .where(
                    col(Transcription.id) == transcription_id,
                    col(Transcription.run_id) == run_id,
                    col(Transcription.status) == expected_status,
                )
                .values(**values)
            )
            session.commit()
            return result.rowcount == 1

    @classmethod
    def claim_transcription(cls, transcription_id: UUID, run_id: UUID | None) -> None:
        with SessionLocal() as session:
            result = session.exec(
                update(Transcription)
                .where(
                    col(Transcription.id) == transcription_id,
                    col(Transcription.run_id) == run_id,
                    col(Transcription.status) == JobStatus.AWAITING_START,
                )
                .values(status=JobStatus.IN_PROGRESS)
            )
            if result.rowcount != 1:
                raise TranscriptionAlreadyStartedError
            session.commit()

    @classmethod
    def is_current_transcription(
        cls,
        transcription_id: UUID,
        run_id: UUID | None,
        status: JobStatus,
    ) -> bool:
        with SessionLocal() as session:
            return (
                session.exec(
                    select(Transcription.id).where(
                        col(Transcription.id) == transcription_id,
                        col(Transcription.run_id) == run_id,
                        col(Transcription.status) == status,
                    )
                ).first()
                is not None
            )

    @classmethod
    async def process_transcription(  # noqa: C901, PLR0912
        cls,
        minute_id: UUID,
        run_id: UUID | None,
        message_data: TranscriptionJobMessageData | TranscriptionReadyMessageData | None = None,
    ) -> TranscriptionJobMessageData:
        """Process a transcription job and save results. Returns True if job is complete, False otherwise."""
        slogger.set_context_field("minute_id", str(minute_id))
        try:
            transcription = cls.get_transcription_from_minute_id(minute_id)
            slogger.set_context_field("transcription_id", str(transcription.id))
            slogger.set_context_field("user_id", str(transcription.user_id))
        except Exception as e:
            raise TranscriptionFailedError from e

        try:
            if isinstance(message_data, TranscriptionJobMessageData):
                # polling an in-flight async job
                if not cls.is_current_transcription(
                    transcription.id,
                    run_id,
                    JobStatus.IN_PROGRESS,
                ):
                    raise StaleTranscriptionRunError
                transcription_job = await transcription_manager.check_transcription(
                    adapter_name=message_data.transcription_service,
                    async_transcription_message_data=message_data,
                )
            elif isinstance(message_data, TranscriptionReadyMessageData):
                # a freshly converted recording handed over by the audio worker
                cls.claim_transcription(transcription.id, run_id)
                transcription_job = await transcription_manager.perform_transcription_steps(
                    transcription=transcription, duration_seconds=message_data.duration_seconds
                )
            else:
                msg = f"Unexpected transcription message data for minute id {minute_id}: {message_data!r}"
                raise TranscriptionFailedError(msg)

            if transcription_job.transcript:
                dialogue_entries = await cls.identify_speakers(transcription_job.transcript)
                meeting_title = await generate_meeting_title(transcript=dialogue_entries)
                updated = cls.update_transcription(
                    transcription.id,
                    run_id,
                    JobStatus.IN_PROGRESS,
                    status=JobStatus.COMPLETED,
                    transcript=dialogue_entries,
                    title=meeting_title,
                )
                if not updated:
                    raise StaleTranscriptionRunError
                capture_event(
                    transcription.user_id,
                    "transcription_succeeded",
                    {"transcriptionId": str(transcription.id)},
                )

        except (StaleTranscriptionRunError, TranscriptionAlreadyStartedError):
            raise
        except Exception as e:
            # Primary failure is logged once at the actor boundary (RayTranscriptionService.process).
            msg = f"Transcription failed: {e!s}"
            try:
                updated = cls.update_transcription(
                    transcription.id,
                    run_id,
                    JobStatus.IN_PROGRESS,
                    status=JobStatus.FAILED,
                    error=msg,
                )
            except Exception:
                slogger.exception("Error updating transcription status. Maybe it doesn't exist?")
            else:
                if not updated:
                    raise StaleTranscriptionRunError from e
                capture_event(
                    transcription.user_id,
                    "transcription_failed",
                    {"transcriptionId": str(transcription.id)},
                )
            raise TranscriptionFailedError from e
        else:
            return transcription_job

    @classmethod
    async def identify_speakers(cls, dialogue_entries: list[DialogueEntry]) -> list[DialogueEntry]:
        try:
            dialogue_entries = await process_speakers_and_dialogue_entries(dialogue_entries)

        except Exception:
            # Do not break flow if this step fails
            slogger.exception("Error processing dialogue entries")
        return dialogue_entries

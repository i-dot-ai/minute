import logging
from uuid import UUID

from sqlalchemy.orm import selectinload
from sqlmodel import col, select

from backend.app.audio.speakers import process_speakers_and_dialogue_entries
from backend.app.llm.client import create_default_chatbot
from backend.app.minutes.prompts import get_chat_with_transcript_system_message
from backend.app.minutes.types import DialogueEntry, TranscriptionJobMessageData
from backend.services.exceptions import InteractionFailedError, TranscriptionFailedError
from backend.services.transcription_services.transcription_manager import TranscriptionServiceManager
from common.database.postgres_database import SessionLocal
from common.database.postgres_models import Chat, JobStatus, Minute, Transcription
from common.settings import get_settings

settings = get_settings()
transcription_manager = TranscriptionServiceManager()
logger = logging.getLogger(__name__)


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
        try:
            chatbot = create_default_chatbot()
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
                chat.assistant_content = chat_response
                chat.status = JobStatus.COMPLETED

                session.add(chat)
                session.commit()
        except Exception as e:
            msg = f"Chat interaction failed: {e!s}"
            logger.exception(msg)
            try:
                chat.status = JobStatus.FAILED
                chat.error = msg
                session.add(chat)
                session.commit()
            except Exception:
                logger.exception("Error updating chat status. Maybe it doesn't exist?")

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
        status: JobStatus | None = None,
        transcript: list[DialogueEntry] | None = None,
        error: str | None = None,
    ) -> None:
        with SessionLocal() as session:
            transcription = session.get(Transcription, transcription_id)
            if not transcription:
                msg = f"transcription id {transcription_id} not found"
                raise ValueError(msg)
            if status:
                transcription.status = status
            if transcript:
                transcription.dialogue_entries = transcript
            if error:
                transcription.error = error
            session.add(transcription)
            session.commit()

    @classmethod
    async def process_transcription(
        cls, minute_id: UUID, async_transcription_message_data: TranscriptionJobMessageData | None = None
    ) -> TranscriptionJobMessageData:
        """Process a transcription job and save results. Returns True if job is complete, False otherwise."""
        try:
            transcription = cls.get_transcription_from_minute_id(minute_id)
        except Exception as e:
            raise TranscriptionFailedError from e

        try:
            if async_transcription_message_data:
                transcription_job = await transcription_manager.check_transcription(
                    adapter_name=async_transcription_message_data.transcription_service,
                    async_transcription_message_data=async_transcription_message_data,
                )
            else:
                # it's a new transcription job
                cls.update_transcription(transcription.id, JobStatus.IN_PROGRESS)
                transcription_job = await transcription_manager.perform_transcription_steps(transcription=transcription)

            if transcription_job.transcript:
                dialogue_entries = await cls.identify_speakers(transcription_job.transcript)
                cls.update_transcription(transcription.id, status=JobStatus.COMPLETED, transcript=dialogue_entries)

        except Exception as e:
            msg = f"Transcription failed: {e!s}"
            logger.exception(msg)
            try:
                cls.update_transcription(transcription.id, status=JobStatus.FAILED, error=msg)
            except Exception:
                logger.exception("Error updating transcription status. Maybe it doesn't exist?")

            raise TranscriptionFailedError from e
        else:
            return transcription_job

    @classmethod
    async def identify_speakers(cls, dialogue_entries: list[DialogueEntry]) -> list[DialogueEntry]:
        try:
            dialogue_entries = await process_speakers_and_dialogue_entries(dialogue_entries)

        except Exception:
            # Do not break flow if this step fails
            logger.exception("Error processing dialogue entries")
        return dialogue_entries

"""Read helpers for the transcription row, and the speaker-naming step the activities use."""

from uuid import UUID

from sqlalchemy.orm import selectinload
from sqlmodel import select

from common.audio.speakers import process_speakers_and_dialogue_entries
from common.database.postgres_database import SessionLocal
from common.database.postgres_models import Minute, Transcription
from common.types import DialogueEntry


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
    async def identify_speakers(cls, dialogue_entries: list[DialogueEntry]) -> list[DialogueEntry]:
        """Raises on LLM failure; the activity retries and the workflow treats speaker naming as optional."""
        return await process_speakers_and_dialogue_entries(dialogue_entries)

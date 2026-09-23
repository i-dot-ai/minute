"""Lightweight transcription status updates.

This module deliberately imports only the database layer and shared types, NOT
the LLM / Azure / ffmpeg stacks pulled in by TranscriptionHandlerService. It lets
lightweight workers (e.g. the ffmpeg worker) mark a transcription as failed without
dragging in the full transcription/LLM dependency tree.
"""

import logging
from uuid import UUID

from common.database.postgres_database import SessionLocal
from common.database.postgres_models import JobStatus, Transcription
from common.types import DialogueEntry

logger = logging.getLogger(__name__)


def update_transcription(
    transcription_id: UUID,
    status: JobStatus | None = None,
    transcript: list[DialogueEntry] | None = None,
    title: str | None = None,
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
        if title:
            transcription.title = title
        session.add(transcription)
        session.commit()

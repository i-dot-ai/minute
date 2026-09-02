"""Read-only MCP tools over a user's own transcripts.

Both tools resolve the caller to a `User` and filter on `user_id`. There is no
write path here on purpose: the credential this server accepts is meant to be
used by a third-party client, so the blast radius is kept to reading the
meetings its owner already has access to in the web app.

Nothing here paginates or truncates. A long meeting comes back whole.

NOTE: this is just a start and a POC. We can of course make everything searchable via bm25.
"""

import uuid
from datetime import datetime
from zoneinfo import ZoneInfo

from fastmcp.exceptions import ToolError
from pydantic import BaseModel, Field
from sqlmodel import col, select

from backend.mcp_server.auth import get_authenticated_user, mcp_session
from common.database.postgres_models import Transcription
from common.format_transcript import transcript_as_speaker_and_utterance
from common.settings import get_structured_logger

logger = get_structured_logger()

# NOTE: fixed stuff - we can change later.
TRANSCRIPTION_NOT_FOUND = "No transcript with that id belongs to you."
UK_TIMEZONE = ZoneInfo("Europe/London")


class TranscriptSummary(BaseModel):
    """One meeting, without its dialogue."""

    id: str = Field(description="Pass this to get_transcript to read the dialogue")
    title: str | None
    created_datetime: datetime
    status: str = Field(description="Transcription job state; only 'completed' meetings have dialogue")


class Transcript(BaseModel):
    """One meeting, with its dialogue."""

    id: str
    title: str | None
    created_datetime: datetime
    status: str
    transcript: str = Field(description="Dialogue as 'Speaker: utterance' lines")


def _in_uk_time(value: datetime | None) -> datetime | None:
    """Read a date or timestamp without a zone as British local time.

    created_datetime is timezone-aware, so a bound has to carry a zone to
    compare against it. One that already does is left alone.
    """
    if value is None:
        return None
    return value.replace(tzinfo=UK_TIMEZONE) if value.tzinfo is None else value


async def list_transcripts(
    start_date: datetime | None = None,
    end_date: datetime | None = None,
) -> list[TranscriptSummary]:
    """List the signed-in user's meeting transcripts, most recent first.

    Both bounds are optional and inclusive, and are read as British local time
    unless they name a timezone; omit them to list every meeting. Returns
    metadata only - use get_transcript to read what was said.
    """
    async with mcp_session() as session:
        user = await get_authenticated_user(session)

        filters = [Transcription.user_id == user.id]
        if start_date is not None:
            filters.append(Transcription.created_datetime >= _in_uk_time(start_date))
        if end_date is not None:
            filters.append(Transcription.created_datetime <= _in_uk_time(end_date))

        statement = select(Transcription).where(*filters).order_by(col(Transcription.created_datetime).desc())
        result = await session.exec(statement)
        transcriptions = result.all()

        logger.info(
            "MCP list_transcripts returned {count} meetings for {email}",
            count=len(transcriptions),
            email=user.email,
        )

        return [
            TranscriptSummary(
                id=str(transcription.id),
                title=transcription.title,
                created_datetime=transcription.created_datetime,
                status=transcription.status,
            )
            for transcription in transcriptions
        ]


async def get_transcript(transcription_id: str) -> Transcript:
    """Read the dialogue of one of the signed-in user's meetings.

    Takes an id from list_transcripts. Returns the whole meeting, which for a
    long one is a lot of text.
    """
    try:
        parsed_id = uuid.UUID(transcription_id)
    except ValueError as e:
        raise ToolError(TRANSCRIPTION_NOT_FOUND) from e

    async with mcp_session() as session:
        user = await get_authenticated_user(session)

        transcription = await session.get(Transcription, parsed_id)
        # Same response either way: whether a given id exists is not something a
        # caller should be able to probe for.
        if transcription is None or transcription.user_id != user.id:
            raise ToolError(TRANSCRIPTION_NOT_FOUND)

        logger.info(
            "MCP get_transcript served {transcription_id} for {email}",
            transcription_id=str(transcription.id),
            email=user.email,
        )

        return Transcript(
            id=str(transcription.id),
            title=transcription.title,
            created_datetime=transcription.created_datetime,
            status=transcription.status,
            transcript=transcript_as_speaker_and_utterance(transcription.dialogue_entries or []),
        )

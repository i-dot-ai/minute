"""Lightweight minute lookups.

This module deliberately imports only the database layer, NOT the LLM / template
stack pulled in by MinuteHandlerService. It lets the transcription worker look up
a MinuteVersion (to enqueue minute generation) without dragging in the full
minute-generation dependency tree.
"""

from uuid import UUID

from sqlalchemy.orm import selectinload

from common.database.postgres_database import SessionLocal
from common.database.postgres_models import Minute, MinuteVersion


def get_only_minute_version_for_minute_id(minute_id: UUID) -> MinuteVersion:
    """Return the single MinuteVersion for a minute, for use during initial generation.

    Raises ValueError if the minute is missing, has no versions, or has more than
    one (this helper is only valid before any additional versions exist).
    """
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

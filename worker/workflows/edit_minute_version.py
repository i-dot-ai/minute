"""Workflow: apply stored AI edit instructions to produce a new minute version.

Same contract as generate_minute_version: "delete" once the message is fully handled
(success or recorded failure), "rehide" when another consumer owns the job, raise only
when recording a failure itself fails.

Log context: the consumer binds minute_version_id (the target version); this workflow
adds minute_id, transcription_id and user_id from the source version.
"""

import asyncio
from typing import Literal
from uuid import UUID

from common.database.postgres_database import AsyncSessionLocal
from common.database.repository import (
    ClaimState,
    claim_version_for_processing,
    get_version_with_transcription,
    mark_version_completed,
    mark_version_failed,
)
from common.services.posthog_client import capture_event
from common.settings import get_structured_logger
from worker.actions.edit_minutes import edit_minutes

slogger = get_structured_logger()

Outcome = Literal["delete", "rehide"]


async def edit_minute_version(  # noqa: PLR0911, C901 - one return per claim state keeps the CAS flow explicit
    target_minute_version_id: UUID,
    source_minute_version_id: UUID,
    llm_slot: asyncio.Semaphore,
    stale_seconds: int,
) -> Outcome:
    async with AsyncSessionLocal() as session:
        try:
            target = await get_version_with_transcription(session, target_minute_version_id)
        except ValueError:
            slogger.warning("Target MinuteVersion no longer exists, nothing to process")
            return "delete"
        try:
            source = await get_version_with_transcription(session, source_minute_version_id)
        except ValueError:
            # The backend validates source ids, but a bogus/deleted source must not
            # loop: record the failure so the user sees it and the message is done.
            slogger.error("Source version for AI edit not found: {source_id}", source_id=str(source_minute_version_id))
            await mark_version_failed(session, target_minute_version_id, "Source version for AI edit not found")
            await session.commit()
            return "delete"
        instructions = target.ai_edit_instructions
        if not instructions or not str(instructions).strip():
            slogger.error("Target minute does not have AI edit instructions")
            await mark_version_failed(
                session, target_minute_version_id, "Target minute does not have AI edit instructions"
            )
            await session.commit()
            return "delete"
        claim = await claim_version_for_processing(session, target_minute_version_id, stale_seconds)
        await session.commit()

    _bind_edit_context(target, source)
    match claim:
        case ClaimState.COMPLETED:
            slogger.info("Minute version already complete, nothing to do")
            return "delete"
        case ClaimState.FAILED:
            slogger.info("Minute version previously failed, waiting for user retry")
            return "delete"
        case ClaimState.MISSING:
            slogger.warning("Minute version row missing, cannot process job")
            return "delete"
        case ClaimState.IN_PROGRESS:
            slogger.info("Another worker owns the minute version, rehiding message")
            return "rehide"
        case ClaimState.CLAIMED:
            slogger.info("AI edit phase started")

    user_id = source.minute.transcription.user_id
    transcription_id = source.minute.transcription.id
    try:
        async with llm_slot:
            edited = await edit_minutes(
                minutes=source.html_content,
                edit_instructions=instructions,
                transcript=source.minute.transcription.dialogue_entries or [],
            )
        async with AsyncSessionLocal() as session:
            await mark_version_completed(session, target_minute_version_id, html_content=edited)
            await session.commit()
    except Exception as e:
        if not await _record_failure(target_minute_version_id, user_id, f"Minute edit failed: {e!s}", transcription_id):
            raise  # recording failed -> redeliver
        return "delete"  # handled: user sees FAILED and can retry
    slogger.info("AI edit phase completed")
    capture_event(user_id, "summary_generation_succeeded", {"transcriptionId": str(transcription_id)})
    return "delete"


def _bind_edit_context(target, source) -> None:
    slogger.set_context_field("source_minute_version_id", str(source.id))
    slogger.set_context_field("minute_id", str(target.minute.id))
    slogger.set_context_field("transcription_id", str(source.minute.transcription.id))
    if source.minute.transcription.user_id:
        slogger.set_context_field("user_id", str(source.minute.transcription.user_id))


async def _record_failure(
    minute_version_id: UUID, user_id: UUID | None, error: str, transcription_id: UUID | None
) -> bool:
    """Returns True when the failure was recorded (handled). False means recording
    itself failed and the caller must let the exception propagate (redelivery)."""
    slogger.error("{error}", error=error)
    try:
        async with AsyncSessionLocal() as session:
            await mark_version_failed(session, minute_version_id, error)
            await session.commit()
    except Exception:
        slogger.exception("Failed to record FAILED status for MinuteVersion")
        return False
    capture_event(user_id, "summary_generation_failed", {"transcriptionId": str(transcription_id)})
    return True

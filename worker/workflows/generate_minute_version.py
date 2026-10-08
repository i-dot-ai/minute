"""Workflow: ensure the transcription exists, then generate the minute version.

One idempotent pipeline shared by all three MINUTE triggers (start, retry, new minute):
the claim CAS routes an already-transcribed recording straight to compose. Returns
"delete" when the message is fully handled (success or a failure that was recorded in
the database - the user sees FAILED and can retry), "rehide" when another consumer owns
the job. Raises only when recording a failure itself fails, so the message is
redelivered rather than dropped.

Claims are two-level by design (see common/database/repository/__init__.py): the
transcription phase claims the transcription row, the compose phase claims the version
row. The consumer heartbeat renews both leases while this workflow runs.

Log context: the consumer binds minute_version_id for the whole task; this workflow
adds minute_id, transcription_id and user_id as soon as it loads the job, so every
log line below (and in the actions it calls) carries the full entity trail.
"""

import asyncio
import tempfile
from pathlib import Path
from typing import Literal
from uuid import UUID

from common.database.postgres_database import AsyncSessionLocal
from common.database.repository import (
    ClaimState,
    claim_transcription_for_processing,
    claim_version_for_processing,
    get_transcription_with_recordings,
    get_version_with_transcription,
    mark_transcription_completed,
    mark_transcription_failed,
    mark_version_completed,
    mark_version_failed,
)
from common.services.posthog_client import capture_event
from common.settings import get_structured_logger
from worker.actions.compose_minutes import compose_minutes
from worker.actions.identify_speakers import identify_speakers
from worker.actions.prepare_audio import prepare_audio
from worker.actions.title_transcript import generate_meeting_title
from worker.actions.transcribe import transcribe_audio

slogger = get_structured_logger()

Outcome = Literal["delete", "rehide"]


async def generate_minute_version(
    minute_version_id: UUID,
    transcription_slot: asyncio.Semaphore,
    llm_slot: asyncio.Semaphore,
    stale_seconds: int,
) -> Outcome:
    async with AsyncSessionLocal() as session:
        try:
            version = await get_version_with_transcription(session, minute_version_id)
        except ValueError:
            slogger.warning("MinuteVersion no longer exists, nothing to process")
            return "delete"  # row gone (e.g. retention cleanup): nothing to process, ever
        transcription = version.minute.transcription
        _bind_job_context(version, transcription)
        claim = await claim_transcription_for_processing(session, transcription.id, stale_seconds)
        await session.commit()

    match claim:
        case ClaimState.FAILED:
            slogger.error("Transcription previously failed; failing the minute version")
            await _fail_version(minute_version_id, "Transcription failed")
            return "delete"
        case ClaimState.MISSING:
            slogger.warning("Transcription row missing, cannot process job")
            return "delete"
        case ClaimState.IN_PROGRESS:
            slogger.info("Another worker owns the transcription, rehiding message")
            return "rehide"
        case ClaimState.COMPLETED:
            slogger.info("Transcription already complete, generating minutes directly")
        case ClaimState.CLAIMED:
            slogger.info("Transcription phase started")
            if not await _transcription_phase(transcription.id, transcription_slot, llm_slot):
                return "delete"  # failure recorded; the user retries from the UI

    return await _compose_phase(minute_version_id, llm_slot, stale_seconds)


def _bind_job_context(version, transcription) -> None:
    slogger.set_context_field("minute_id", str(version.minute.id))
    slogger.set_context_field("transcription_id", str(transcription.id))
    if transcription.user_id:
        slogger.set_context_field("user_id", str(transcription.user_id))


async def _transcription_phase(
    transcription_id: UUID,
    transcription_slot: asyncio.Semaphore,
    llm_slot: asyncio.Semaphore,
) -> bool:
    """prepare_audio -> transcribe (T-slot) -> identify_speakers -> title (L-slot) -> persist.

    Returns True when the transcription COMPLETED. Returns False when a failure was
    recorded in the database (handled - the caller must NOT proceed to compose).
    Raises only when recording the failure itself failed, so the message is redelivered."""
    user_id = None
    try:
        async with transcription_slot:
            # tmpdir is held open across prepare and transcribe: the STT call needs the file
            with tempfile.TemporaryDirectory() as tempdir:
                async with AsyncSessionLocal() as session:
                    transcription = await get_transcription_with_recordings(session, transcription_id)
                user_id = transcription.user_id
                prepared = await prepare_audio(transcription, work_dir=Path(tempdir))
                entries = await transcribe_audio(prepared.file_path)
        async with llm_slot:
            entries = await identify_speakers(entries)
            title = await generate_meeting_title(entries)
        async with AsyncSessionLocal() as session:
            await mark_transcription_completed(session, transcription_id, transcript=entries, title=title)
            await session.commit()
    except Exception as e:
        if not await _record_transcription_failure(transcription_id, user_id, f"Transcription failed: {e!s}"):
            raise  # recording failed -> redeliver rather than dropping the job
        return False  # handled: caller returns "delete" and does NOT compose
    slogger.info(
        "Transcription phase completed: {num_entries} dialogue entries, title_generated={has_title}, "
        "title_length={title_length}",
        num_entries=len(entries),
        has_title=bool(title),
        title_length=len(title),
    )
    capture_event(user_id, "transcription_succeeded", {"transcriptionId": str(transcription_id)})
    return True


async def _record_transcription_failure(transcription_id: UUID, user_id: UUID | None, error: str) -> bool:
    """Returns True when the failure was recorded (handled). False means recording
    itself failed and the caller must let the exception propagate (redelivery)."""
    slogger.error("{error}", error=error)
    try:
        async with AsyncSessionLocal() as session:
            await mark_transcription_failed(session, transcription_id, error)
            await session.commit()
    except Exception:
        slogger.exception("Failed to record FAILED status for transcription")
        return False
    capture_event(user_id, "transcription_failed", {"transcriptionId": str(transcription_id)})
    return True


async def _compose_phase(minute_version_id: UUID, llm_slot: asyncio.Semaphore, stale_seconds: int) -> Outcome:
    async with AsyncSessionLocal() as session:
        claim = await claim_version_for_processing(session, minute_version_id, stale_seconds)
        await session.commit()

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
            slogger.info("Minute generation phase started")

    user_id = None
    transcription_id = None
    try:
        async with AsyncSessionLocal() as session:
            version = await get_version_with_transcription(session, minute_version_id)
            user_id = version.minute.transcription.user_id
            transcription_id = version.minute.transcription.id
            await session.commit()
        async with llm_slot:
            html = await compose_minutes(version.minute)
        async with AsyncSessionLocal() as session:
            await mark_version_completed(session, minute_version_id, html_content=html)
            await session.commit()
    except Exception as e:
        if not await _record_version_failure(
            minute_version_id, user_id, f"Minute generation failed: {e!s}", transcription_id
        ):
            raise  # recording failed -> redeliver
        return "delete"  # handled: user sees FAILED and can retry
    slogger.info("Minute generation phase completed")
    capture_event(user_id, "summary_generation_succeeded", {"transcriptionId": str(transcription_id)})
    return "delete"


async def _record_version_failure(
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


async def _fail_version(minute_version_id: UUID, error: str) -> None:
    async with AsyncSessionLocal() as session:
        await mark_version_failed(session, minute_version_id, error)
        await session.commit()

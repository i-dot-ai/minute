import logging
import math
import uuid
from datetime import UTC, datetime, timedelta
from typing import Annotated

from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import update
from sqlalchemy.orm import selectinload
from sqlmodel import col, func, or_, select
from sqlmodel.ext.asyncio.session import AsyncSession

from backend.api.dependencies import SessionDep, StorageDep, UserDep
from backend.utils import temporal
from common.database.postgres_models import Minute, MinuteVersion, Recording, Transcription, UserTemplate
from common.services.storage.s3 import exists
from common.settings import get_settings
from common.types import (
    JobStatus,
    PaginatedTranscriptionsResponse,
    TranscriptionCreateRequest,
    TranscriptionCreateResponse,
    TranscriptionGetResponse,
    TranscriptionListFilter,
    TranscriptionMetadata,
    TranscriptionPatchRequest,
    TranscriptionRetryRequest,
)

settings = get_settings()


transcriptions_router = APIRouter(tags=["Transcriptions"])

logger = logging.getLogger(__name__)


def _next_cleanup_cutoff(retention_days: int) -> datetime:
    """Records created before this instant get deleted at the next cleanup run (23:00 UTC daily)."""
    now = datetime.now(UTC)
    next_run = now.replace(hour=23, minute=0, second=0, microsecond=0)
    if next_run <= now:
        next_run += timedelta(days=1)
    return next_run - timedelta(days=retention_days)


async def _enqueue_transcription(session: AsyncSession, transcription: Transcription, minute_id: uuid.UUID) -> None:
    """Commit before starting the workflow so the worker can always see the job row."""
    await session.commit()
    try:
        await temporal.start_transcription_workflow(transcription.id, minute_id)
    except Exception as exc:
        transcription.status = JobStatus.FAILED
        transcription.error = "Failed to enqueue transcription"
        await session.commit()
        raise HTTPException(status_code=503, detail="Failed to enqueue transcription") from exc


@transcriptions_router.get("/transcriptions", response_model=PaginatedTranscriptionsResponse)
async def list_transcriptions(
    session: SessionDep,
    current_user: UserDep,
    page: Annotated[int, Query(ge=1, description="Page number (starts from 1)")] = 1,
    page_size: Annotated[int, Query(ge=1, le=100, description="Number of items per page")] = 20,
    filter_by: Annotated[TranscriptionListFilter | None, Query()] = None,
    search: Annotated[str | None, Query(max_length=100, description="Match against transcription title")] = None,
) -> PaginatedTranscriptionsResponse:
    """Get paginated metadata for transcriptions for the current user."""

    offset = (page - 1) * page_size

    expiry_cutoff = (
        _next_cleanup_cutoff(current_user.data_retention_days) if current_user.data_retention_days is not None else None
    )

    # Retention disabled but caller wants only-expiring -> nothing qualifies.
    if filter_by == TranscriptionListFilter.EXPIRING_SOON and expiry_cutoff is None:
        return PaginatedTranscriptionsResponse(items=[], total_count=0, page=page, page_size=page_size, total_pages=1)

    filters = [Transcription.user_id == current_user.id]
    if filter_by == TranscriptionListFilter.EXPIRING_SOON:  # expiry_cutoff is not None here
        filters.append(Transcription.created_datetime < expiry_cutoff)
    elif filter_by == TranscriptionListFilter.FAILED:
        filters.append(Transcription.status == JobStatus.FAILED)

    search_term = search.strip() if search else None
    if search_term:
        escaped = search_term.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        filters.append(
            or_(
                col(Transcription.title).ilike(f"%{escaped}%"),
                # pg_trgm gives typo tolerance, e.g. "budjet" still matches "Budget review".
                # `%` is similarity() >= pg_trgm.similarity_threshold, but unlike the bare
                # function call it can use the trigram index. The threshold is a GUC, set from
                # SEARCH_SIMILARITY_THRESHOLD for every connection in postgres_database.py.
                col(Transcription.title).op("%", is_comparison=True)(search_term),
            )
        )

    count_statement = select(func.count(col(Transcription.id))).where(*filters)
    statement = (
        select(Transcription)
        .where(*filters)
        .order_by(col(Transcription.created_datetime).desc())
        .offset(offset)
        .limit(page_size)
    )

    count_result = await session.exec(count_statement)
    total_count = count_result.one()
    result = await session.exec(statement)
    transcriptions = result.all()

    items = [
        TranscriptionMetadata(
            id=t.id,
            created_datetime=t.created_datetime,
            title=t.title,
            text=t.dialogue_entries[0]["text"][:100] if t.dialogue_entries else "",
            status=t.status,
            expiring=expiry_cutoff is not None and t.created_datetime < expiry_cutoff,
        )
        for t in transcriptions
    ]

    total_pages = math.ceil(total_count / page_size) or 1

    return PaginatedTranscriptionsResponse(
        items=items,
        total_count=total_count,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@transcriptions_router.post("/transcriptions", response_model=TranscriptionCreateResponse, status_code=201)
async def create_transcription(
    request: TranscriptionCreateRequest,
    session: SessionDep,
    current_user: UserDep,
    storage: StorageDep,
) -> TranscriptionCreateResponse:
    """Start a transcription job."""
    # FOR UPDATE: serialise concurrent creates for this recording (so only one can
    # claim it) and participate in the orphan-cleanup lock protocol, so cleanup and
    # this association cannot interleave into a broken transcription.
    recording = (
        await session.exec(select(Recording).where(Recording.id == request.recording_id).with_for_update())
    ).first()
    if not recording or recording.user_id != current_user.id:
        raise HTTPException(404, detail="Recording not found")
    # A recording belongs to exactly one transcription: re-submitting it must not
    # re-link the audio (orphaning the first transcription and re-queueing work).
    if recording.transcription_id is not None:
        raise HTTPException(status_code=409, detail="Recording has already been transcribed")
    transcription = Transcription(user_id=current_user.id, title=request.title)

    if not await exists(storage, recording.s3_file_key):
        raise HTTPException(
            status_code=404,
            detail=f"Recording file not found in S3: {recording.s3_file_key}",
        )

    if request.template_id is not None:
        template = (
            await session.exec(
                select(UserTemplate).where(
                    UserTemplate.id == request.template_id,
                    UserTemplate.user_id == current_user.id,
                )
            )
        ).first()
        if template is None:
            msg = f"User template not found: {request.template_id}"
            raise HTTPException(status_code=404, detail=msg)

    minute = Minute(
        template_name=request.template_name,
        user_template_id=request.template_id,
        agenda=request.agenda,
        transcription_id=transcription.id,
    )
    minute_version = MinuteVersion(minute_id=minute.id)
    session.add(transcription)
    session.add(minute)
    session.add(minute_version)
    recording.transcription_id = transcription.id
    await _enqueue_transcription(session, transcription, minute.id)

    return TranscriptionCreateResponse(id=transcription.id)


@transcriptions_router.post(
    "/transcriptions/{transcription_id}/retry",
    response_model=TranscriptionCreateResponse,
    status_code=201,
)
async def retry_transcription(
    transcription_id: uuid.UUID,
    request: TranscriptionRetryRequest,
    session: SessionDep,
    current_user: UserDep,
    storage: StorageDep,
) -> TranscriptionCreateResponse:
    """Re-run a failed transcription in place, reusing the existing recording and id."""
    transcription = (
        await session.exec(
            select(Transcription)
            .where(Transcription.id == transcription_id)
            .options(
                selectinload(Transcription.recordings),
                selectinload(Transcription.minutes).selectinload(Minute.minute_versions),
            )
        )
    ).first()
    if not transcription or transcription.user_id != current_user.id:
        raise HTTPException(404, detail="Transcription not found")
    if transcription.status != JobStatus.FAILED:
        raise HTTPException(400, detail="Only failed transcriptions can be retried")

    recording = transcription.recordings[0] if transcription.recordings else None
    if not recording:
        raise HTTPException(400, detail="Transcription has no recording to retry")
    if not await exists(storage, recording.s3_file_key):
        raise HTTPException(404, detail=f"Recording file not found in S3: {recording.s3_file_key}")

    minute = transcription.minutes[0] if transcription.minutes else None
    if not minute:
        raise HTTPException(400, detail="Transcription has no minute to retry")
    # The worker's transcription path expects the queued minute to hold exactly
    # one version (its initial generation). A failed transcription always meets
    # this, but guard explicitly so a multi-version minute is never re-queued
    # into a state the worker cannot process.
    if len(minute.minute_versions) != 1:
        raise HTTPException(400, detail="Transcription cannot be retried in its current state")

    if request.template_id is not None:
        template = (
            await session.exec(
                select(UserTemplate).where(
                    UserTemplate.id == request.template_id,
                    UserTemplate.user_id == current_user.id,
                )
            )
        ).first()
        if template is None:
            msg = f"User template not found: {request.template_id}"
            raise HTTPException(status_code=404, detail=msg)

    # Atomic FAILED -> AWAITING_START transition: only one concurrent retry can
    # win, so exactly one request ever publishes retry work.
    retry_claim = await session.exec(
        update(Transcription)
        .where(Transcription.id == transcription.id, Transcription.status == JobStatus.FAILED)
        .values(status=JobStatus.AWAITING_START)
    )
    if retry_claim.rowcount != 1:
        await session.rollback()
        raise HTTPException(400, detail="Only failed transcriptions can be retried")
    transcription.status = JobStatus.AWAITING_START
    transcription.error = None
    transcription.dialogue_entries = None
    transcription.created_datetime = datetime.now(UTC)

    minute.template_name = request.template_name
    minute.user_template_id = request.template_id
    minute.agenda = request.agenda

    minute_version = minute.minute_versions[0]
    minute_version.status = JobStatus.AWAITING_START
    minute_version.error = None
    minute_version.html_content = ""

    await _enqueue_transcription(session, transcription, minute.id)

    return TranscriptionCreateResponse(id=transcription.id)


@transcriptions_router.get("/transcriptions/{transcription_id}", response_model=TranscriptionGetResponse)
async def get_transcription(
    transcription_id: uuid.UUID,
    session: SessionDep,
    current_user: UserDep,
) -> TranscriptionGetResponse:
    """Get a specific transcription by ID."""
    transcription = await session.get(Transcription, transcription_id)
    if not transcription or transcription.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Transcription not found")
    return TranscriptionGetResponse(
        id=transcription.id,
        status=transcription.status,
        dialogue_entries=transcription.dialogue_entries,
        title=transcription.title,
        created_datetime=transcription.created_datetime,
        error=transcription.error,
    )


@transcriptions_router.patch("/transcriptions/{transcription_id}", response_model=Transcription)
async def save_transcription(
    transcription_id: uuid.UUID,
    transcription_data: TranscriptionPatchRequest,
    session: SessionDep,
    current_user: UserDep,
):
    """Save or update a transcription."""
    logger.info("saving transcription for user %s", current_user.id)
    # Use the transcription service to handle the save operation
    transcription = await session.get(Transcription, transcription_id)
    if not transcription or transcription.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Transcription not found")
    # updated_datetime is the worker's claim token (common/services/job_claim.py): any
    # write while the job is processing would silently void the worker's claim.
    if transcription.status in (JobStatus.AWAITING_START, JobStatus.IN_PROGRESS):
        raise HTTPException(status_code=409, detail="Transcription cannot be edited while it is processing")

    if transcription_data.title is not None:
        transcription.title = transcription_data.title
    if transcription_data.dialogue_entries is not None:
        transcription.dialogue_entries = transcription_data.dialogue_entries
    await session.commit()
    await session.refresh(transcription)

    return transcription


@transcriptions_router.delete("/transcriptions/{transcription_id}", status_code=204)
async def delete_transcription(transcription_id: uuid.UUID, session: SessionDep, current_user: UserDep):
    """Delete a specific transcription by ID."""
    # First check if the transcription exists and belongs to the user
    transcription = await session.get(Transcription, transcription_id)
    if not transcription or transcription.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Transcription not found")

    # Delete the transcription
    await session.delete(transcription)
    await session.commit()

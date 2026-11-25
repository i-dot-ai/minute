import math
import uuid
from datetime import UTC, datetime, timedelta
from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, Response
from sqlalchemy import tuple_, update
from sqlalchemy.orm import selectinload
from sqlmodel import col, func, or_, select

from backend.api.dependencies import SQLSessionDep, UserDep
from backend.api.dependencies.authorization import authorize_resource
from backend.utils import temporal
from backend.utils.transcription_search import matching_sources, search_patterns, search_previews
from common.authz import (
    Action,
    query_actor_permissions,
)
from common.database.postgres_models import (
    JobStatus,
    Minute,
    MinuteVersion,
    Recording,
    Transcription,
    UserTemplate,
)
from common.services.storage_services import get_storage_service
from common.settings import get_settings, get_structured_logger
from common.types import (
    PaginatedTranscriptionSearchResponse,
    PaginatedTranscriptionsResponse,
    TranscriptionCreateRequest,
    TranscriptionCreateResponse,
    TranscriptionGetResponse,
    TranscriptionListFilter,
    TranscriptionMetadata,
    TranscriptionPatchRequest,
    TranscriptionRetryRequest,
    TranscriptionSearchResult,
    TranscriptionSearchSource,
)

from .enqueue import enqueue_transcription
from .filters import visible_transcriptions_filter

settings = get_settings()

storage_service = get_storage_service(settings.STORAGE_SERVICE_NAME)

transcriptions_router = APIRouter(tags=["Transcriptions"])

logger = get_structured_logger()
SEARCH_BATCH_SIZE = 50


def _next_cleanup_cutoff(retention_days: int) -> datetime:
    """Records created before this instant get deleted at the next cleanup run (23:00 UTC daily)."""
    now = datetime.now(UTC)
    next_run = now.replace(hour=23, minute=0, second=0, microsecond=0)
    if next_run <= now:
        next_run += timedelta(days=1)
    return next_run - timedelta(days=retention_days)


async def _check_retry_workflow(transcription_id: uuid.UUID) -> None:
    try:
        running = await temporal.transcription_workflow_running(transcription_id)
    except Exception as exc:
        raise HTTPException(503, detail="Could not check transcription workflow; please try again") from exc
    if running:
        raise HTTPException(409, detail="The previous transcription is still finishing; please try again shortly")


@transcriptions_router.get("/transcriptions", response_model=PaginatedTranscriptionsResponse)
async def list_transcriptions(
    session: SQLSessionDep,
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

    actor_permissions = await query_actor_permissions(session, current_user)
    filters = [visible_transcriptions_filter(actor_permissions)]
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
            meeting_datetime=t.meeting_datetime,
            title=t.title,
            text=t.dialogue_entries[0]["text"][:100] if t.dialogue_entries else "",
            status=t.status,
            expiring=expiry_cutoff is not None and t.created_datetime < expiry_cutoff,
            no_speech_detected=t.no_speech_detected,
            org_id=t.org_id,
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


@transcriptions_router.get("/transcriptions/search", response_model=PaginatedTranscriptionSearchResponse)
async def search_transcriptions(  # noqa: C901 # Keep matching and page validation together.
    session: SQLSessionDep,
    current_user: UserDep,
    response: Response,
    search: Annotated[str, Query(min_length=1, max_length=100, description="All keywords within one source document")],
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
    filter_by: Annotated[TranscriptionListFilter | None, Query()] = None,
    sources: Annotated[
        tuple[TranscriptionSearchSource, ...],
        Query(min_length=1, description="Repeat for multiple sources. Defaults to all four sources."),
    ] = tuple(TranscriptionSearchSource),
) -> PaginatedTranscriptionSearchResponse:
    """Search selected sources within the current user's transcriptions.

    Keywords are literal, case-insensitive substrings; they can span transcript entries,
    but cannot be combined across sources, speaker labels or summary versions.
    Speakers match stored labels, not mentions in speech. Results rank title, speaker,
    summary, then transcript, newest first within each rank.
    """
    response.headers["Cache-Control"] = "private, no-store"
    patterns = search_patterns(search)
    if not patterns:
        raise HTTPException(422, detail="Search must contain at least one keyword")

    expiry_cutoff = (
        _next_cleanup_cutoff(current_user.data_retention_days) if current_user.data_retention_days is not None else None
    )
    actor_permissions = await query_actor_permissions(session, current_user)
    filters = [visible_transcriptions_filter(actor_permissions)]
    if filter_by == TranscriptionListFilter.EXPIRING_SOON:
        if expiry_cutoff is None:
            return PaginatedTranscriptionSearchResponse(
                items=[], total_count=0, page=page, page_size=page_size, total_pages=1
            )
        filters.append(Transcription.created_datetime < expiry_cutoff)
    elif filter_by == TranscriptionListFilter.FAILED:
        filters.append(Transcription.status == JobStatus.FAILED)

    statement = (
        select(Transcription)
        .where(*filters)
        .order_by(col(Transcription.created_datetime).desc(), col(Transcription.id).desc())
    )
    if TranscriptionSearchSource.SUMMARY in sources:
        statement = statement.options(
            selectinload(Transcription.minutes).selectinload(
                Minute.minute_versions.and_(MinuteVersion.status == JobStatus.COMPLETED)
            )
        )
    ids_by_source = {source: [] for source in ("title", "speaker", "summary", "transcript")}
    selected = set(sources)
    result_offset = (page - 1) * page_size
    batch_statement = statement.limit(SEARCH_BATCH_SIZE)
    # shortcut: pilot scans the user's content for exact counts; add indexed search text when latency warrants it.
    while batch := (await session.exec(batch_statement)).all():
        for transcription in batch:
            first = next(matching_sources(transcription, patterns, selected), None)
            if first is None:
                continue
            ids_by_source[first[0]].append(transcription.id)
        last = batch[-1]
        batch_statement = statement.where(
            tuple_(Transcription.created_datetime, Transcription.id) < (last.created_datetime, last.id)
        ).limit(SEARCH_BATCH_SIZE)

    ranked_ids = [transcription_id for source_ids in ids_by_source.values() for transcription_id in source_ids]
    page_ids = ranked_ids[result_offset : result_offset + page_size]
    page_order = {transcription_id: index for index, transcription_id in enumerate(page_ids)}
    page_statement = statement.where(col(Transcription.id).in_(page_ids)).execution_options(populate_existing=True)
    page_transcriptions = (await session.exec(page_statement)).all() if page_ids else []
    items = []
    for transcription in sorted(page_transcriptions, key=lambda transcription: page_order[transcription.id]):
        matches, truncated = search_previews(matching_sources(transcription, patterns, selected), patterns)
        if not matches:
            continue
        items.append(
            TranscriptionSearchResult(
                id=transcription.id,
                title=transcription.title,
                created_datetime=transcription.created_datetime,
                meeting_datetime=transcription.meeting_datetime,
                status=transcription.status,
                text=transcription.dialogue_entries[0]["text"][:100] if transcription.dialogue_entries else "",
                expiring=expiry_cutoff is not None and transcription.created_datetime < expiry_cutoff,
                no_speech_detected=transcription.no_speech_detected,
                matches=matches,
                matches_truncated=truncated,
                org_id=transcription.org_id,
            )
        )
    total_count = len(ranked_ids)
    return PaginatedTranscriptionSearchResponse(
        items=items,
        total_count=total_count,
        page=page,
        page_size=page_size,
        total_pages=math.ceil(total_count / page_size) or 1,
    )


@transcriptions_router.post("/transcriptions", response_model=TranscriptionCreateResponse, status_code=201)
async def create_transcription(
    request: TranscriptionCreateRequest,
    session: SQLSessionDep,
    current_user: UserDep,
) -> TranscriptionCreateResponse:
    """Start a transcription job."""
    # FOR UPDATE: serialise concurrent creates for this recording (so only one can
    # claim it) and participate in the orphan-cleanup lock protocol, so cleanup and
    # this association cannot interleave into a broken transcription.
    recording_row = (
        await session.exec(select(Recording).where(Recording.id == request.recording_id).with_for_update())
    ).first()
    recording = await authorize_resource(session, current_user.id, recording_row, Action.EDIT)
    # A recording belongs to exactly one transcription: re-submitting it must not
    # re-link the audio (orphaning the first transcription and re-queueing work).
    if recording.transcription_id is not None:
        raise HTTPException(status_code=409, detail="Recording has already been transcribed")
    transcription = Transcription(user_id=current_user.id, title=request.title, org_id=recording.org_id)
    # Left unset, the column defaults to now (the upload time). Setting None would insert NULL.
    if request.meeting_datetime is not None:
        transcription.meeting_datetime = request.meeting_datetime

    if not await storage_service.check_object_exists(recording.s3_file_key):
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
    await enqueue_transcription(session, transcription, minute_version)

    return TranscriptionCreateResponse(id=transcription.id)


@transcriptions_router.post(
    "/transcriptions/{transcription_id}/retry",
    response_model=TranscriptionCreateResponse,
    status_code=201,
)
async def retry_transcription(
    transcription_id: uuid.UUID,
    request: TranscriptionRetryRequest,
    session: SQLSessionDep,
    current_user: UserDep,
) -> TranscriptionCreateResponse:
    """Re-run a failed transcription in place, reusing the existing recording and id."""
    transcription_row = (
        await session.exec(
            select(Transcription)
            .where(Transcription.id == transcription_id)
            .options(
                selectinload(Transcription.recordings),
                selectinload(Transcription.minutes).selectinload(Minute.minute_versions),
            )
        )
    ).first()
    transcription = await authorize_resource(session, current_user.id, transcription_row, Action.EDIT)
    if transcription.status != JobStatus.FAILED:
        raise HTTPException(400, detail="Only failed transcriptions can be retried")
    await _check_retry_workflow(transcription.id)

    recording = transcription.recordings[0] if transcription.recordings else None
    if not recording:
        raise HTTPException(400, detail="Transcription has no recording to retry")
    if not await storage_service.check_object_exists(recording.s3_file_key):
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

    # Fence against the row we read: a newer attempt may already have failed again.
    retry_claim = await session.exec(
        update(Transcription)
        .where(
            Transcription.id == transcription.id,
            Transcription.status == JobStatus.FAILED,
            Transcription.updated_datetime == transcription.updated_datetime,
        )
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

    await enqueue_transcription(session, transcription, minute_version)

    return TranscriptionCreateResponse(id=transcription.id)


@transcriptions_router.get("/transcriptions/{transcription_id}", response_model=TranscriptionGetResponse)
async def get_transcription(
    transcription_id: uuid.UUID,
    session: SQLSessionDep,
    current_user: UserDep,
) -> TranscriptionGetResponse:
    """Get a specific transcription by ID."""
    transcription_row = await session.get(Transcription, transcription_id)
    transcription = await authorize_resource(session, current_user.id, transcription_row, Action.READ)
    return TranscriptionGetResponse(
        id=transcription.id,
        status=transcription.status,
        dialogue_entries=transcription.dialogue_entries,
        title=transcription.title,
        meeting_datetime=transcription.meeting_datetime,
        created_datetime=transcription.created_datetime,
        error=transcription.error,
        no_speech_detected=transcription.no_speech_detected,
        org_id=transcription.org_id,
    )


@transcriptions_router.patch("/transcriptions/{transcription_id}", response_model=TranscriptionGetResponse)
async def save_transcription(
    transcription_id: uuid.UUID,
    transcription_data: TranscriptionPatchRequest,
    session: SQLSessionDep,
    current_user: UserDep,
) -> TranscriptionGetResponse:
    """Save or update a transcription."""
    logger.info("Saving transcription")
    # Use the transcription service to handle the save operation
    transcription_row = await session.get(Transcription, transcription_id)
    transcription = await authorize_resource(session, current_user.id, transcription_row, Action.EDIT)
    # The workflow writes the row (speakers, title) while it is processing, so an edit now
    # would race those writes.
    if transcription.status in (JobStatus.AWAITING_START, JobStatus.IN_PROGRESS):
        raise HTTPException(status_code=409, detail="Transcription cannot be edited while it is processing")

    if transcription_data.title is not None:
        transcription.title = transcription_data.title
    if transcription_data.dialogue_entries is not None:
        transcription.dialogue_entries = transcription_data.dialogue_entries
    if transcription_data.meeting_datetime is not None:
        transcription.meeting_datetime = transcription_data.meeting_datetime
    await session.commit()
    await session.refresh(transcription)

    return TranscriptionGetResponse(
        id=transcription.id,
        status=transcription.status,
        dialogue_entries=transcription.dialogue_entries,
        title=transcription.title,
        meeting_datetime=transcription.meeting_datetime,
        created_datetime=transcription.created_datetime,
        error=transcription.error,
        no_speech_detected=transcription.no_speech_detected,
        org_id=transcription.org_id,
    )


@transcriptions_router.delete("/transcriptions/{transcription_id}", status_code=204)
async def delete_transcription(transcription_id: uuid.UUID, session: SQLSessionDep, current_user: UserDep):
    """Delete a specific transcription by ID."""
    # First check if the transcription exists and the caller may delete it
    transcription_row = await session.get(Transcription, transcription_id)
    transcription = await authorize_resource(session, current_user.id, transcription_row, Action.DELETE)

    # Delete the transcription
    await session.delete(transcription)
    await session.commit()

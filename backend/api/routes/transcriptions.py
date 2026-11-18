import math
import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, Response
from sqlalchemy import tuple_, update
from sqlalchemy.orm import selectinload
from sqlmodel import col, func, or_, select
from sqlmodel.ext.asyncio.session import AsyncSession

from backend.api.dependencies import SQLSessionDep, UserDep
from backend.utils import temporal
from backend.utils.get_file_s3_key import get_file_s3_key
from backend.utils.transcription_search import matching_sources, search_patterns, search_previews
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
    RecordingCreateRequest,
    RecordingCreateResponse,
    SingleRecording,
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


async def _enqueue_transcription(
    session: AsyncSession, transcription: Transcription, minute_version: MinuteVersion
) -> None:
    """Commit before starting the workflow so the worker can always see the job row."""
    await session.commit()
    try:
        await temporal.start_transcription_workflow(
            transcription.id,
            minute_version.minute_id,
            user_id=transcription.user_id,
            minute_version_id=minute_version.id,
        )
    except Exception as exc:
        transcription.status = JobStatus.FAILED
        transcription.error = "Failed to enqueue transcription"
        await session.commit()
        raise HTTPException(status_code=503, detail="Failed to enqueue transcription") from exc


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
            no_speech_detected=t.no_speech_detected,
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
    filters = [Transcription.user_id == current_user.id]
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
                status=transcription.status,
                text=transcription.dialogue_entries[0]["text"][:100] if transcription.dialogue_entries else "",
                expiring=expiry_cutoff is not None and transcription.created_datetime < expiry_cutoff,
                no_speech_detected=transcription.no_speech_detected,
                matches=matches,
                matches_truncated=truncated,
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


@transcriptions_router.post("/recordings")
async def create_recording(
    request: RecordingCreateRequest, session: SQLSessionDep, user: UserDep
) -> RecordingCreateResponse:
    recording_id = uuid.uuid4()
    file_name = f"{recording_id}.{request.file_extension}"
    user_upload_s3_file_key = get_file_s3_key(user.email, file_name)
    recording = Recording(user_id=user.id, s3_file_key=user_upload_s3_file_key)
    session.add(recording)
    await session.commit()
    presigned_url = await storage_service.generate_presigned_url_put_object(user_upload_s3_file_key, 3600)
    await session.refresh(recording)
    return RecordingCreateResponse(id=recording.id, upload_url=presigned_url)


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
    recording = (
        await session.exec(select(Recording).where(Recording.id == request.recording_id).with_for_update())
    ).first()
    if not recording or recording.user_id != current_user.id:
        raise HTTPException(404, detail="Recording not found")
    # A recording belongs to exactly one transcription: re-submitting it must not
    # re-link the audio (orphaning the first transcription and re-queueing work).
    if recording.transcription_id is not None:
        raise HTTPException(status_code=409, detail="Recording has already been transcribed")
    transcription = Transcription(user_id=current_user.id, title=request.title, meeting_date=request.meeting_date)

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
    await _enqueue_transcription(session, transcription, minute_version)

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

    await _enqueue_transcription(session, transcription, minute_version)

    return TranscriptionCreateResponse(id=transcription.id)


@transcriptions_router.get("/transcriptions/{transcription_id}", response_model=TranscriptionGetResponse)
async def get_transcription(
    transcription_id: uuid.UUID,
    session: SQLSessionDep,
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
        meeting_date=transcription.meeting_date,
        created_datetime=transcription.created_datetime,
        error=transcription.error,
        no_speech_detected=transcription.no_speech_detected,
    )


@transcriptions_router.get("/transcriptions/{transcription_id}/recordings")
async def get_recordings_for_transcription(
    transcription_id: uuid.UUID, session: SQLSessionDep, user: UserDep
) -> list[SingleRecording]:
    transcription = await session.get(Transcription, transcription_id)
    if not transcription or transcription.user_id != user.id:
        raise HTTPException(404)

    result = await session.exec(
        select(Recording)
        .where(Recording.transcription_id == transcription.id)
        .order_by(col(Recording.created_datetime).desc())
    )
    recordings = result.all()
    # Only return oldest of each file type
    # So users only see original mp3 file if it was converted due to multiple channels
    recordings = {Path(recording.s3_file_key).suffix: recording for recording in recordings}.values()
    signed_recordings: list[SingleRecording] = []
    for recording in recordings:
        if not await storage_service.check_object_exists(recording.s3_file_key):
            continue
        key_path = Path(recording.s3_file_key)
        filename = f"{transcription.title}{key_path.suffix}" if transcription.title else key_path.name
        presigned_url = await storage_service.generate_presigned_url_get_object(
            recording.s3_file_key, filename, 60 * 60 * 12
        )
        signed_recordings.append(SingleRecording(id=recording.id, url=presigned_url, extension=key_path.suffix))

    return signed_recordings


@transcriptions_router.patch("/transcriptions/{transcription_id}", response_model=Transcription)
async def save_transcription(
    transcription_id: uuid.UUID,
    transcription_data: TranscriptionPatchRequest,
    session: SQLSessionDep,
    current_user: UserDep,
):
    """Save or update a transcription."""
    logger.info("Saving transcription")
    # Use the transcription service to handle the save operation
    transcription = await session.get(Transcription, transcription_id)
    if not transcription or transcription.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Transcription not found")
    # The workflow writes the row (speakers, title) while it is processing, so an edit now
    # would race those writes.
    if transcription.status in (JobStatus.AWAITING_START, JobStatus.IN_PROGRESS):
        raise HTTPException(status_code=409, detail="Transcription cannot be edited while it is processing")

    if transcription_data.title is not None:
        transcription.title = transcription_data.title
    if transcription_data.dialogue_entries is not None:
        transcription.dialogue_entries = transcription_data.dialogue_entries
    # Unlike title, an explicit null clears the date, so check the field was sent.
    if "meeting_date" in transcription_data.model_fields_set:
        transcription.meeting_date = transcription_data.meeting_date
    await session.commit()
    await session.refresh(transcription)

    return transcription


@transcriptions_router.delete("/transcriptions/{transcription_id}", status_code=204)
async def delete_transcription(transcription_id: uuid.UUID, session: SQLSessionDep, current_user: UserDep):
    """Delete a specific transcription by ID."""
    # First check if the transcription exists and belongs to the user
    transcription = await session.get(Transcription, transcription_id)
    if not transcription or transcription.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Transcription not found")

    # Delete the transcription
    await session.delete(transcription)
    await session.commit()

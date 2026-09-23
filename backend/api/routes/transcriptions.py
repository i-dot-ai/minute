import logging
import math
import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, HTTPException, Query
from sqlmodel import col, func, or_, select

from backend.api.dependencies import SQLSessionDep, UserDep
from backend.utils.get_file_s3_key import get_file_s3_key
from common.database.postgres_models import (
    JobStatus,
    Minute,
    MinuteVersion,
    Recording,
    RecordingStatus,
    Transcription,
)
from common.services.queue_services import get_queue_service
from common.services.storage_services import get_storage_service
from common.settings import get_settings
from common.types import (
    PaginatedTranscriptionsResponse,
    PipelineStageStatus,
    QueueDepth,
    RecordingCreateRequest,
    RecordingCreateResponse,
    SingleRecording,
    TaskType,
    TranscriptionCreateRequest,
    TranscriptionCreateResponse,
    TranscriptionGetResponse,
    TranscriptionListFilter,
    TranscriptionMetadata,
    TranscriptionPatchRequest,
    TranscriptionStatusResponse,
    WorkerMessage,
)

settings = get_settings()

storage_service = get_storage_service(settings.STORAGE_SERVICE_NAME)


transcriptions_router = APIRouter(tags=["Transcriptions"])
transcription_queue_service = get_queue_service(
    settings.TRANSCRIPTION_QUEUE_NAME, settings.TRANSCRIPTION_DEADLETTER_QUEUE_NAME
)
transcription_ready_queue_service = get_queue_service(
    settings.TRANSCRIPTION_READY_QUEUE_NAME, settings.TRANSCRIPTION_READY_DEADLETTER_QUEUE_NAME
)
llm_queue_service = get_queue_service(settings.LLM_QUEUE_NAME, settings.LLM_DEADLETTER_QUEUE_NAME)

logger = logging.getLogger(__name__)


def _next_cleanup_cutoff(retention_days: int) -> datetime:
    """Records created before this instant get deleted at the next cleanup run (23:00 UTC daily)."""
    now = datetime.now(UTC)
    next_run = now.replace(hour=23, minute=0, second=0, microsecond=0)
    if next_run <= now:
        next_run += timedelta(days=1)
    return next_run - timedelta(days=retention_days)


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
    recording = await session.get(Recording, request.recording_id)
    if not recording or recording.user_id != current_user.id:
        raise HTTPException(404, detail="Recording not found")
    transcription = Transcription(user_id=current_user.id, title=request.title)

    if not await storage_service.check_object_exists(recording.s3_file_key):
        raise HTTPException(
            status_code=404,
            detail=f"Recording file not found in S3: {recording.s3_file_key}",
        )

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
    await session.commit()
    transcription_queue_service.publish_message(WorkerMessage(id=minute.id, type=TaskType.AUDIO_PREPROCESSING))

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
        created_datetime=transcription.created_datetime,
    )


def _collect_queue_depths() -> list[QueueDepth]:
    """Read approximate depths for all pipeline queues. Best-effort; never raises."""
    queues = [
        ("transcription", transcription_queue_service),
        ("transcription_ready", transcription_ready_queue_service),
        ("llm", llm_queue_service),
    ]
    out: list[QueueDepth] = []
    for name, service in queues:
        try:
            depth = service.get_queue_depth()
            out.append(QueueDepth(name=name, **depth))
        except Exception:
            logger.exception("Failed to read queue depth for %s", name)
            out.append(QueueDepth(name=name, visible=-1, in_flight=-1, delayed=-1, deadletter=-1))
    return out


def _preprocessing_stage(recordings: list[Recording]) -> tuple[PipelineStageStatus, bool]:
    """Stage 1: audio preprocessing, tracked on the recording rows. Returns (stage, done)."""
    if not recordings:
        return (
            PipelineStageStatus(
                stage="preprocessing",
                status="missing",
                detail="No recording row exists for this transcription.",
            ),
            False,
        )

    newest = recordings[0]
    ready = any(r.status == RecordingStatus.READY_FOR_TRANSCRIPTION for r in recordings)
    failed = any(r.status == RecordingStatus.FAILED_PROCESSING for r in recordings)
    if failed:
        status, detail = "failed", "Audio preprocessing failed for a recording."
    elif ready:
        status, detail = "completed", "Audio preprocessed and ready for transcription."
    else:
        status, detail = (
            "waiting",
            f"Recording uploaded (status={newest.status}); waiting for the audio worker to pick it up.",
        )
    return (
        PipelineStageStatus(
            stage="preprocessing", status=status, detail=detail, updated_datetime=newest.created_datetime
        ),
        ready,
    )


def _transcription_stage(transcription: Transcription, preprocessing_done: bool) -> PipelineStageStatus:
    """Stage 2: Transcription, tracked on the transcription row."""
    if transcription.status == JobStatus.COMPLETED:
        status, detail = "completed", "Transcript generated."
    elif transcription.status == JobStatus.FAILED:
        status, detail = "failed", transcription.error or "Transcription failed."
    elif transcription.status == JobStatus.IN_PROGRESS:
        status, detail = "in_progress", "Transcription worker is processing the audio."
    elif preprocessing_done:
        status, detail = (
            "waiting",
            "Audio is ready but the transcription worker has not started it. "
            "Check the transcription worker is running and consuming the transcription-ready queue.",
        )
    else:
        status, detail = "blocked", "Waiting on preprocessing to finish before transcription can start."
    return PipelineStageStatus(
        stage="transcription", status=status, detail=detail, updated_datetime=transcription.updated_datetime
    )


def _minute_stage(transcription: Transcription, minute_versions: list[MinuteVersion]) -> PipelineStageStatus:
    """Stage 3: Minute generation, tracked on minute versions."""
    if not minute_versions:
        return PipelineStageStatus(stage="minute_generation", status="missing", detail="No minute version rows found.")

    newest = minute_versions[0]
    if newest.status == JobStatus.COMPLETED:
        status, detail = "completed", "Minutes generated."
    elif newest.status == JobStatus.FAILED:
        status, detail = "failed", newest.error or "Minute generation failed."
    elif newest.status == JobStatus.IN_PROGRESS:
        status, detail = "in_progress", "LLM worker is generating minutes."
    elif transcription.status == JobStatus.COMPLETED:
        status, detail = (
            "waiting",
            "Transcript ready but minute generation has not started. Check the LLM worker and the llm queue.",
        )
    else:
        status, detail = "blocked", "Waiting on transcription to complete."
    return PipelineStageStatus(
        stage="minute_generation", status=status, detail=detail, updated_datetime=newest.updated_datetime
    )


def _build_pipeline_stages(
    transcription: Transcription,
    recordings: list[Recording],
    minute_versions: list[MinuteVersion],
) -> tuple[list[PipelineStageStatus], str]:
    """Derive per-stage status and a one-line summary from persisted state."""
    preprocessing_stage, preprocessing_done = _preprocessing_stage(recordings)
    stages = [
        preprocessing_stage,
        _transcription_stage(transcription, preprocessing_done),
        _minute_stage(transcription, minute_versions),
    ]

    # One-line summary: first non-terminal stage explains where we are stuck.
    summary = "Pipeline complete."
    for stage in stages:
        if stage.status in {"failed", "missing"}:
            summary = f"Stuck at {stage.stage}: {stage.detail}"
            break
        if stage.status in {"waiting", "blocked", "in_progress"}:
            summary = f"At {stage.stage} ({stage.status}): {stage.detail}"
            break
    return stages, summary


@transcriptions_router.get(
    "/transcriptions/{transcription_id}/status", response_model=TranscriptionStatusResponse
)
async def get_transcription_status(
    transcription_id: uuid.UUID,
    session: SQLSessionDep,
    current_user: UserDep,
) -> TranscriptionStatusResponse:
    """Diagnostic view of a transcription's execution across the whole pipeline.

    Shows each stage (preprocessing -> transcription -> minute generation), what state
    it is in and when it last changed, plus live queue depths so you can see what is
    waiting or in-flight and where a job is stuck.
    """
    transcription = await session.get(Transcription, transcription_id)
    if not transcription or transcription.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Transcription not found")

    recordings_result = await session.exec(
        select(Recording)
        .where(Recording.transcription_id == transcription_id)
        .order_by(col(Recording.created_datetime).desc())
    )
    recordings = list(recordings_result.all())

    mv_result = await session.exec(
        select(MinuteVersion)
        .join(Minute, col(MinuteVersion.minute_id) == col(Minute.id))
        .where(Minute.transcription_id == transcription_id)
        .order_by(col(MinuteVersion.updated_datetime).desc())
    )
    minute_versions = list(mv_result.all())

    stages, summary = _build_pipeline_stages(transcription, recordings, minute_versions)

    recording_views = [
        {
            "id": str(r.id),
            "s3_file_key": r.s3_file_key,
            "status": str(r.status),
            "created_datetime": r.created_datetime.isoformat() if r.created_datetime else None,
        }
        for r in recordings
    ]

    return TranscriptionStatusResponse(
        transcription_id=transcription.id,
        transcription_status=transcription.status,
        title=transcription.title,
        created_datetime=transcription.created_datetime,
        updated_datetime=transcription.updated_datetime,
        error=transcription.error,
        recordings=recording_views,
        stages=stages,
        queues=_collect_queue_depths(),
        summary=summary,
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
    logger.info("saving transcription for user %s", current_user.id)
    # Use the transcription service to handle the save operation
    transcription = await session.get(Transcription, transcription_id)
    if not transcription or transcription.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Transcription not found")

    if transcription_data.title is not None:
        transcription.title = transcription_data.title
    if transcription_data.dialogue_entries is not None:
        transcription.dialogue_entries = transcription_data.dialogue_entries
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

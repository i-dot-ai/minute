import logging
import math
import uuid
from pathlib import Path

from fastapi import APIRouter, HTTPException, Query
from sqlmodel import col, func, select

from backend.api.dependencies import SQLSessionDep, UserDep
from backend.utils.get_file_s3_key import get_file_s3_key
from common.database.postgres_models import (
    Minute,
    MinuteVersion,
    Recording,
    Transcription,
)
from common.services.queue_services import get_queue_service
from common.services.storage_services import get_storage_service
from common.settings import get_settings
from common.types import (
    PaginatedTranscriptionsResponse,
    RecordingCreateRequest,
    RecordingCreateResponse,
    SingleRecording,
    TaskType,
    TranscriptionCreateRequest,
    TranscriptionCreateResponse,
    TranscriptionGetResponse,
    TranscriptionMetadata,
    TranscriptionPatchRequest,
    WorkerMessage,
)

settings = get_settings()

storage_service = get_storage_service(settings.STORAGE_SERVICE_NAME)


transcriptions_router = APIRouter(tags=["Transcriptions"])
transcription_queue_service = get_queue_service(
    settings.QUEUE_SERVICE_NAME, settings.TRANSCRIPTION_QUEUE_NAME, settings.TRANSCRIPTION_DEADLETTER_QUEUE_NAME
)

logger = logging.getLogger(__name__)


@transcriptions_router.get("/transcriptions", response_model=PaginatedTranscriptionsResponse)
async def list_transcriptions(
    session: SQLSessionDep,
    current_user: UserDep,
    page: int = Query(1, ge=1, description="Page number (starts from 1)"),
    page_size: int = Query(20, ge=1, le=100, description="Number of items per page"),
) -> PaginatedTranscriptionsResponse:
    """Get paginated metadata for transcriptions for the current user."""
    count_statement = select(func.count(col(Transcription.id))).where(Transcription.user_id == current_user.id)
    count_result = await session.exec(count_statement)
    total_count = count_result.one()

    offset = (page - 1) * page_size
    statement = (
        select(Transcription)
        .where(Transcription.user_id == current_user.id)
        .order_by(col(Transcription.created_datetime).desc())
        .offset(offset)
        .limit(page_size)
    )
    result = await session.exec(statement)
    transcriptions = result.all()

    items = [
        TranscriptionMetadata(
            id=t.id,
            created_datetime=t.created_datetime,
            title=t.title,
            text=t.dialogue_entries[0]["text"][:100] if t.dialogue_entries else "",
            status=t.status,
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
    transcription_queue_service.publish_message(WorkerMessage(id=minute.id, type=TaskType.TRANSCRIPTION))

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

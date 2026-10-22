import uuid
from pathlib import Path

from fastapi import APIRouter, HTTPException
from sqlmodel import col, select

from backend.api.dependencies import SessionDep, StorageDep, UserDep
from backend.utils.get_file_s3_key import get_file_s3_key
from common.database.postgres_models import Recording, Transcription
from common.services.storage.s3 import (
    exists,
    generate_presigned_url_get_object,
    generate_presigned_url_put_object,
)
from common.types import RecordingCreateRequest, RecordingCreateResponse, SingleRecording

recordings_router = APIRouter(tags=["Recordings"])


@recordings_router.post("/recordings")
async def create_recording(
    request: RecordingCreateRequest, session: SessionDep, user: UserDep, storage: StorageDep
) -> RecordingCreateResponse:
    recording_id = uuid.uuid4()
    file_name = f"{recording_id}.{request.file_extension}"
    user_upload_s3_file_key = get_file_s3_key(user.email, file_name)
    recording = Recording(user_id=user.id, s3_file_key=user_upload_s3_file_key)
    session.add(recording)
    await session.commit()
    presigned_url = await generate_presigned_url_put_object(storage, user_upload_s3_file_key, 3600)
    await session.refresh(recording)
    return RecordingCreateResponse(id=recording.id, upload_url=presigned_url)


@recordings_router.get("/transcriptions/{transcription_id}/recordings")
async def get_recordings_for_transcription(
    transcription_id: uuid.UUID, session: SessionDep, user: UserDep, storage: StorageDep
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
        if not await exists(storage, recording.s3_file_key):
            continue
        key_path = Path(recording.s3_file_key)
        filename = f"{transcription.title}{key_path.suffix}" if transcription.title else key_path.name
        presigned_url = await generate_presigned_url_get_object(storage, recording.s3_file_key, filename, 60 * 60 * 12)
        signed_recordings.append(SingleRecording(id=recording.id, url=presigned_url, extension=key_path.suffix))

    return signed_recordings

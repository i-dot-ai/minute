import tempfile
import uuid
from pathlib import Path
from uuid import UUID

import sentry_sdk
from sqlalchemy.orm import selectinload
from sqlmodel import col, select

from audio_worker import ffmpeg_utils
from common.database.postgres_database import SessionLocal
from common.database.postgres_models import JobStatus, Minute, Recording, Transcription
from common.services.queue_services.base import QueueService
from common.services.storage_services import get_storage_service
from common.settings import get_settings, get_structured_logger
from common.types import TaskType, TranscriptionReadyMessageData, WorkerMessage

slogger = get_structured_logger()
settings = get_settings()
storage_service = get_storage_service(settings.STORAGE_SERVICE_NAME)

SUPPORTED_FORMATS = {".mp3"}


class AudioConversionFailedError(Exception):
    """Raised when a recording cannot be prepared for transcription."""


class AudioService:
    """Pulls CONVERT jobs off the audio queue, normalises the recording to a mono mp3 with ffmpeg,
    then hands the transcription over to the Ray transcription worker.

    Intentionally simple: one message at a time, no Ray. Scale horizontally by running more tasks.
    """

    def __init__(self, audio_queue_service: QueueService, transcription_queue_service: QueueService) -> None:
        self.audio_queue_service = audio_queue_service
        self.transcription_queue_service = transcription_queue_service

    async def process_message(self, message: WorkerMessage) -> None:
        transcription_id = message.id
        slogger.set_context_field("transcription_id", str(transcription_id))
        slogger.info("Received audio conversion job for transcription")
        try:
            recording, minute_id = self._load_recording_and_minute(transcription_id)
            slogger.set_context_field("minute_id", str(minute_id))
            slogger.set_context_field("user_id", str(recording.user_id))
            duration_seconds = await self._prepare_recording(recording)
        except Exception as e:
            msg = f"Audio conversion failed for transcription id {transcription_id}: {e!s}"
            slogger.exception("Audio conversion failed for transcription")
            self._mark_transcription_failed(transcription_id, msg)
            raise AudioConversionFailedError(msg) from e

        self.transcription_queue_service.publish_message(
            WorkerMessage(
                id=minute_id,
                type=TaskType.TRANSCRIPTION,
                data=TranscriptionReadyMessageData(duration_seconds=duration_seconds),
            )
        )
        slogger.info("Handed transcription to the transcription queue")

    @staticmethod
    def _load_recording_and_minute(transcription_id: UUID) -> tuple[Recording, UUID]:
        """Resolve the recording to convert and the minute id the transcription worker expects.

        Mirrors the previous inline behaviour: newest recording first (recordings[0]) and the
        single up-front minute created by the backend.
        """
        with SessionLocal() as session:
            transcription = session.exec(
                select(Transcription)
                .where(Transcription.id == transcription_id)
                .options(selectinload(Transcription.recordings))
            ).first()
            if transcription is None:
                msg = f"transcription id {transcription_id} not found"
                raise AudioConversionFailedError(msg)
            if not transcription.recordings:
                msg = f"transcription id {transcription_id} has no recording!"
                raise AudioConversionFailedError(msg)
            minute_id = session.exec(
                select(Minute.id)
                .where(Minute.transcription_id == transcription_id)
                .order_by(col(Minute.created_datetime).desc())
            ).first()
            if minute_id is None:
                msg = f"transcription id {transcription_id} has no minute!"
                raise AudioConversionFailedError(msg)
            recording = transcription.recordings[0]
            session.expunge(recording)
            return recording, minute_id

    async def _prepare_recording(self, recording: Recording) -> float:
        """Download the source, convert to mono mp3 if needed, and return the audio duration.

        When conversion happens a new Recording row is created for the converted file, so the
        transcription worker's recordings[0] is always a transcription-ready mono mp3.
        """
        file_extension = Path(recording.s3_file_key).suffix.lower()

        with tempfile.TemporaryDirectory() as tempdir:
            temp_file_path = Path(tempdir) / Path(recording.s3_file_key).name
            await storage_service.download(recording.s3_file_key, temp_file_path)

            num_channels = ffmpeg_utils.get_num_audio_channels(temp_file_path)
            if file_extension in SUPPORTED_FORMATS and num_channels == 1:
                return ffmpeg_utils.get_duration(temp_file_path)

            with sentry_sdk.start_transaction(op="process", name="convert_mp3") as transaction:
                transaction.set_data("file_extension", file_extension)
                new_file_path = ffmpeg_utils.convert_to_mp3(temp_file_path)

            duration = ffmpeg_utils.get_duration(new_file_path)
            new_recording_id = uuid.uuid4()
            new_s3_key = str(Path(recording.s3_file_key).with_name(f"{new_recording_id}.mp3"))
            await storage_service.upload(new_s3_key, new_file_path)
            with SessionLocal() as session:
                new_recording = Recording(
                    id=new_recording_id,
                    s3_file_key=new_s3_key,
                    user_id=recording.user_id,
                    transcription_id=recording.transcription_id,
                )
                session.add(new_recording)
                session.commit()
            return duration

    @staticmethod
    def _mark_transcription_failed(transcription_id: UUID, error: str) -> None:
        try:
            with SessionLocal() as session:
                transcription = session.get(Transcription, transcription_id)
                if transcription is None:
                    slogger.warning("Could not mark transcription failed: not found")
                    return
                transcription.status = JobStatus.FAILED
                transcription.error = error
                session.add(transcription)
                session.commit()
        except Exception:
            slogger.exception("Error updating transcription status. Maybe it doesn't exist?")

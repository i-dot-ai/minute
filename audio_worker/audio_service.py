import asyncio
import tempfile
import uuid
from pathlib import Path
from uuid import UUID

import sentry_sdk
from sqlalchemy.dialects.postgresql import insert

from audio_worker import ffmpeg_utils
from common.database.postgres_database import SessionLocal
from common.database.postgres_models import JobStatus, Recording, Transcription
from common.services.posthog_client import capture_event
from common.services.queue_services.base import QueueService
from common.services.storage_services import get_storage_service
from common.settings import get_settings, get_structured_logger
from common.types import AudioWorkerMessage, TaskType, TranscriptionReadyMessageData, WorkerMessage

slogger = get_structured_logger()
settings = get_settings()
storage_service = get_storage_service(settings.STORAGE_SERVICE_NAME)

SUPPORTED_FORMATS = {".mp3"}


class AudioConversionFailedError(Exception):
    """Raised when a recording cannot be prepared for, or handed over to, transcription.

    ``marked_failed`` records whether the transcription is now in a terminal state (FAILED, or
    gone entirely). When it is False the failure could not be recorded, so the caller should
    leave the message on the queue to be redelivered rather than silently dropping the job.
    """

    def __init__(self, msg: str, *, marked_failed: bool) -> None:
        super().__init__(msg)
        self.marked_failed = marked_failed


class InvalidAudioError(Exception):
    """Raised when ffmpeg cannot convert an uploaded recording."""


class AudioService:
    """Pulls CONVERT jobs off the audio queue, normalises the recording to a mono mp3 with ffmpeg,
    then hands the transcription over to the Ray transcription worker.

    Intentionally simple: one message at a time, no Ray. Scale horizontally by running more tasks.
    """

    def __init__(
        self,
        audio_queue_service: QueueService[AudioWorkerMessage],
        transcription_queue_service: QueueService[WorkerMessage],
    ) -> None:
        self.audio_queue_service = audio_queue_service
        self.transcription_queue_service = transcription_queue_service

    async def process_message(self, message: AudioWorkerMessage) -> None:
        """Convert the recording and hand it to the transcription queue.

        Invalid media is terminal and raises AudioConversionFailedError after marking the
        transcription FAILED. Infrastructure errors propagate for redelivery.
        """
        slogger.info("Received audio conversion job for transcription")
        slogger.set_context_field("user_id", str(message.user_id))
        slogger.set_context_field("transcription_id", str(message.transcription_id))
        slogger.set_context_field("minute_id", str(message.minute_id))

        try:
            duration_seconds = await self._prepare_recording(message)
        except InvalidAudioError as e:
            msg = f"Audio conversion failed for transcription id {message.transcription_id}: {e!s}"
            marked_failed = self._mark_transcription_failed(message.transcription_id, msg)
            capture_event(
                message.user_id,
                "transcription_failed",
                {"transcriptionId": str(message.transcription_id), "stage": "audio_conversion"},
            )
            raise AudioConversionFailedError(msg, marked_failed=marked_failed) from e

        self.transcription_queue_service.publish_message(
            WorkerMessage(
                id=message.minute_id,
                type=TaskType.TRANSCRIPTION,
                data=TranscriptionReadyMessageData(duration_seconds=duration_seconds),
            )
        )

        slogger.info("Handed transcription to the transcription queue")

    async def _prepare_recording(self, message: AudioWorkerMessage) -> float:
        """Download the source, convert to mono mp3 if needed, and return the audio duration.

        ffmpeg/ffprobe are blocking subprocesses, so they run in a thread to keep the event loop free.

        When conversion happens a new Recording row is created for the converted file, so the
        transcription worker's recordings[0] is always a transcription-ready mono mp3.
        """
        file_extension = Path(message.s3_file_key).suffix.lower()

        with tempfile.TemporaryDirectory() as tempdir:
            temp_file_path = Path(tempdir) / Path(message.s3_file_key).name
            await storage_service.download(message.s3_file_key, temp_file_path)

            # ffmpeg/ffprobe block, so run them off-thread to keep the async worker responsive.
            num_channels = await asyncio.to_thread(ffmpeg_utils.get_num_audio_channels, temp_file_path)
            if file_extension in SUPPORTED_FORMATS and num_channels == 1:
                return await asyncio.to_thread(ffmpeg_utils.get_duration, temp_file_path)

            with sentry_sdk.start_transaction(op="process", name="convert_mp3") as transaction:
                transaction.set_data("file_extension", file_extension)
                try:
                    new_file_path = await asyncio.to_thread(ffmpeg_utils.convert_to_mp3, temp_file_path)
                except Exception as exc:
                    msg = f"Could not convert recording: {exc!s}"
                    raise InvalidAudioError(msg) from exc

            duration = await asyncio.to_thread(ffmpeg_utils.get_duration, new_file_path)
            new_recording_id = uuid.uuid5(uuid.NAMESPACE_URL, f"minute:converted-recording:{message.transcription_id}")
            new_s3_key = str(Path(message.s3_file_key).with_name(f"{new_recording_id}.mp3"))
            await storage_service.upload(new_s3_key, new_file_path)
            try:
                with SessionLocal() as session:
                    session.exec(
                        insert(Recording)
                        .values(
                            id=new_recording_id,
                            s3_file_key=new_s3_key,
                            user_id=message.user_id,
                            transcription_id=message.transcription_id,
                        )
                        .on_conflict_do_nothing(index_elements=["id"])
                    )
                    session.commit()
            except Exception:
                try:
                    await storage_service.delete(new_s3_key)
                except Exception:
                    slogger.exception("Failed to remove converted audio after database failure")
                raise
            return duration

    @staticmethod
    def _mark_transcription_failed(transcription_id: UUID, error: str) -> bool:
        """Mark the transcription FAILED. Returns False only if the update itself errored.

        A transcription that no longer exists (e.g. deleted by the user) counts as handled:
        there is nothing left to retry.
        """
        try:
            with SessionLocal() as session:
                transcription = session.get(Transcription, transcription_id)
                if transcription is None:
                    slogger.warning("Could not mark transcription failed: not found")
                    return True
                transcription.status = JobStatus.FAILED
                transcription.error = error
                session.add(transcription)
                session.commit()
        except Exception:
            slogger.exception("Error updating transcription status to FAILED")
            return False
        return True

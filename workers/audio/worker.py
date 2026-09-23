import asyncio
import logging
import tempfile
import uuid
from pathlib import Path

from sqlalchemy.orm import selectinload

from common.database.postgres_database import SessionLocal
from common.database.postgres_models import JobStatus, Minute, Recording, RecordingStatus, Transcription
from common.services.queue_services.sqs import SQSQueueService
from common.services.storage_services import get_storage_service
from common.services.transcription_status import update_transcription
from common.settings import get_settings
from common.types import TaskType, WorkerMessage
from workers.audio.audio import convert_to_mp3, get_num_audio_channels
from workers.base_worker import BaseWorker, PoisonMessageError
from workers.signal_handler import SignalHandler

logger = logging.getLogger(__name__)
settings = get_settings()
storage_service = get_storage_service(settings.STORAGE_SERVICE_NAME)
SUPPORTED_FORMATS = {".mp3"}


class AudioWorker(BaseWorker):
    """CPU-bound worker that preprocesses audio files.

    Reads from the transcription queue, converts audio to MP3 mono if needed, then
    publishes to the transcription-ready queue. Processes one file at a time.
    """

    max_messages = 1

    def __init__(
        self,
        transcription_queue_service: SQSQueueService,
        transcription_ready_queue_service: SQSQueueService,
        signal_handler: SignalHandler | None = None,
    ):
        super().__init__(transcription_queue_service, signal_handler)
        self.transcription_ready_queue_service = transcription_ready_queue_service

    async def process_message(self, message: WorkerMessage) -> None:
        """Process audio preprocessing for a recording."""
        logger.info("Processing audio preprocessing for minute id: %s", message.id)

        with SessionLocal() as session:
            recording = self._get_recording_for_minute(session, message.id)
            if not recording:
                # No recording to work on: this message can never succeed.
                msg = f"Recording not found for minute id: {message.id}"
                raise PoisonMessageError(msg)

            if recording.status == RecordingStatus.READY_FOR_TRANSCRIPTION:
                logger.info("Recording %s already processed, publishing to transcription-ready queue", recording.id)
                self._publish_to_transcription_ready_queue(message.id)
                return

            file_extension = Path(recording.s3_file_key).suffix.lower()

            try:
                with tempfile.TemporaryDirectory() as tempdir:
                    temp_file_path = Path(tempdir) / Path(recording.s3_file_key).name
                    await storage_service.download(recording.s3_file_key, temp_file_path)
                    await self._process_audio_if_needed(
                        recording=recording,
                        temp_file_path=temp_file_path,
                        file_extension=file_extension,
                        session=session,
                    )
            except Exception:
                # Audio preprocessing failed for this recording. Mark both the recording
                # and the transcription as failed so the UI does not hang, then let the
                # base worker abandon/redrive the message.
                logger.exception("Failed to preprocess audio for recording %s", recording.id)
                recording.status = RecordingStatus.FAILED_PROCESSING
                session.add(recording)
                session.commit()
                if recording.transcription_id:
                    self._mark_transcription_failed(
                        recording.transcription_id, "Audio preprocessing (FFmpeg) failed"
                    )
                raise

            logger.info("Audio preprocessing complete for minute id %s", message.id)

        self._publish_to_transcription_ready_queue(message.id)

    def _get_recording_for_minute(self, session, minute_id: uuid.UUID) -> Recording | None:
        """Get the recording for a given minute ID."""
        minute = session.get(
            Minute,
            minute_id,
            options=[selectinload(Minute.transcription).selectinload(Transcription.recordings)],
        )

        if not minute or not minute.transcription or not minute.transcription.recordings:
            return None

        return minute.transcription.recordings[0]

    async def _process_audio_if_needed(
        self,
        recording: Recording,
        temp_file_path: Path,
        file_extension: str,
        session,
    ) -> None:
        """Convert audio to MP3 mono if needed. Marks the resulting recording ready."""
        num_channels = await asyncio.to_thread(get_num_audio_channels, temp_file_path)

        if file_extension in SUPPORTED_FORMATS and num_channels == 1:
            logger.info("Recording %s already in supported format", recording.id)
            recording.status = RecordingStatus.READY_FOR_TRANSCRIPTION
            session.add(recording)
            session.commit()
            return

        logger.info("Converting recording %s to MP3 mono", recording.id)

        new_file_path = await asyncio.to_thread(convert_to_mp3, temp_file_path)

        new_recording_id = uuid.uuid4()
        new_s3_key = str(Path(recording.s3_file_key).with_name(f"{new_recording_id}.mp3"))

        await storage_service.upload(new_s3_key, new_file_path)

        new_recording = Recording(
            id=new_recording_id,
            s3_file_key=new_s3_key,
            user_id=recording.user_id,
            transcription_id=recording.transcription_id,
            status=RecordingStatus.READY_FOR_TRANSCRIPTION,
        )
        session.add(new_recording)
        session.commit()

        logger.info("Created new converted recording %s", new_recording_id)

    def _mark_transcription_failed(self, transcription_id: uuid.UUID, error: str) -> None:
        try:
            update_transcription(
                transcription_id, status=JobStatus.FAILED, error=error
            )
        except Exception:
            logger.exception("Failed to mark transcription %s as failed", transcription_id)

    def _publish_to_transcription_ready_queue(self, minute_id: uuid.UUID) -> None:
        """Publish message to the transcription-ready queue."""
        self.transcription_ready_queue_service.publish_message(
            WorkerMessage(id=minute_id, type=TaskType.TRANSCRIPTION)
        )

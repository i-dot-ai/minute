from audio_worker.audio_service import AudioService
from audio_worker.healthcheck import HEARTBEAT_DIR, ensure_heartbeat_dir
from audio_worker.signal_handler import SignalHandler
from common.services.queue_services import get_queue_service
from common.settings import get_settings, get_structured_logger

settings = get_settings()

slogger = get_structured_logger()


class AudioWorkerService:
    """Single-process, single-message-at-a-time loop for the audio (ffmpeg) worker.

    Deliberately not Ray-based: run one process per task and scale horizontally by
    increasing the number of ECS tasks.
    """

    def __init__(self) -> None:
        self.signal_handler = SignalHandler()
        self.audio_queue_service = get_queue_service(
            settings.QUEUE_SERVICE_NAME, settings.AUDIO_QUEUE_NAME, settings.AUDIO_DEADLETTER_QUEUE_NAME
        )
        self.transcription_queue_service = get_queue_service(
            settings.QUEUE_SERVICE_NAME,
            settings.TRANSCRIPTION_QUEUE_NAME,
            settings.TRANSCRIPTION_DEADLETTER_QUEUE_NAME,
        )
        self.audio_service = AudioService(
            audio_queue_service=self.audio_queue_service,
            transcription_queue_service=self.transcription_queue_service,
        )
        ensure_heartbeat_dir()
        self.heartbeat_path = HEARTBEAT_DIR / "audio_worker_main.heartbeat"
        self.heartbeat_path.touch()

    async def run(self) -> None:
        slogger.info("Audio worker started. Polling audio queue {queue_name}", queue_name=settings.AUDIO_QUEUE_NAME)
        while not self.signal_handler.signal_received:
            messages = self.audio_queue_service.receive_message(max_messages=1)
            for message, receipt_handle in messages:
                slogger.refresh_context()
                slogger.set_context_field("transcription_id", str(message.id))
                try:
                    await self.audio_service.process_message(message)
                except Exception:
                    # Known and unexpected failures alike: the transcription is already marked
                    # FAILED where possible. Complete the message so it does not loop; SQS
                    # redrive still moves genuinely poisonous messages to the DLQ on retry.
                    slogger.exception("Audio conversion failed for message")
                self.audio_queue_service.complete_message(receipt_handle)
            self.heartbeat_path.touch()

        slogger.info("Signal received. Audio worker shutting down.")

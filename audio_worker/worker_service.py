import asyncio
import threading
from pathlib import Path

from audio_worker.audio_service import AudioConversionFailedError, AudioService
from audio_worker.healthcheck import HEARTBEAT_DIR
from audio_worker.signal_handler import SignalHandler
from common.services.queue_services import get_queue_service
from common.services.queue_services.base import QueueService
from common.settings import get_settings, get_structured_logger
from common.types import AudioWorkerMessage

settings = get_settings()

slogger = get_structured_logger()

HEARTBEAT_INTERVAL_SECONDS = 30


class AudioWorker:
    """Single-process, single-message-at-a-time loop for the audio (ffmpeg) worker.

    Deliberately not Ray-based: run one process per task and scale horizontally by
    increasing the number of ECS tasks.
    """

    def __init__(
        self,
        audio_queue_service: QueueService[AudioWorkerMessage] | None = None,
        transcription_queue_service: QueueService | None = None,
        heartbeat_path: Path | None = None,
    ) -> None:
        self.signal_handler = SignalHandler()
        self.audio_queue_service = audio_queue_service or get_queue_service(
            queue_service_name=settings.QUEUE_SERVICE_NAME,
            queue_name=settings.AUDIO_QUEUE_NAME,
            deadletter_queue_name=settings.AUDIO_DEADLETTER_QUEUE_NAME,
            message_model=AudioWorkerMessage,
        )
        self.transcription_queue_service = transcription_queue_service or get_queue_service(
            queue_service_name=settings.QUEUE_SERVICE_NAME,
            queue_name=settings.TRANSCRIPTION_QUEUE_NAME,
            deadletter_queue_name=settings.TRANSCRIPTION_DEADLETTER_QUEUE_NAME,
        )
        self.audio_service = AudioService(
            audio_queue_service=self.audio_queue_service,
            transcription_queue_service=self.transcription_queue_service,
        )
        if heartbeat_path is None:
            HEARTBEAT_DIR.mkdir(parents=True, exist_ok=True)
            heartbeat_path = HEARTBEAT_DIR / "audio_worker_main.heartbeat"
        self.heartbeat_path = heartbeat_path
        self.heartbeat_path.touch()
        self._stop_heartbeat = threading.Event()

    async def run(self) -> None:
        slogger.info("Audio worker started. Polling audio queue {queue_name}", queue_name=settings.AUDIO_QUEUE_NAME)
        # Heartbeat independently of the poll/convert loop so blocking I/O cannot starve it.
        self._stop_heartbeat.clear()
        heartbeat_thread = threading.Thread(
            target=self._heartbeat,
            name="audio-worker-heartbeat",
            daemon=True,
        )
        heartbeat_thread.start()
        try:
            while not self.signal_handler.signal_received:
                await self.poll_once()
        finally:
            self._stop_heartbeat.set()
            heartbeat_thread.join(timeout=HEARTBEAT_INTERVAL_SECONDS + 1)
            self.heartbeat_path.unlink(missing_ok=True)
            self.audio_queue_service.close(force=self.signal_handler.signal_received)
            self.transcription_queue_service.close()

        slogger.info("Signal received. Audio worker shutting down.")

    async def poll_once(self) -> None:
        # receive_message is a blocking long-poll (up to 20s on SQS); run it off the event
        # loop so heartbeats keep flowing and other tasks sharing the loop (e.g. in tests)
        # are not starved.
        messages = await asyncio.to_thread(self.audio_queue_service.receive_message, max_messages=1)
        for message, receipt_handle in messages:
            if self.signal_handler.signal_received:
                # Shutting down: hand the message straight back rather than starting a
                # conversion that SIGKILL would interrupt.
                self.audio_queue_service.abandon_message(receipt_handle)
                continue
            await self.handle_message(message, receipt_handle)

    async def handle_message(self, message: AudioWorkerMessage, receipt_handle: object) -> None:
        slogger.refresh_context()
        slogger.set_context_field("user_id", str(message.user_id))
        slogger.set_context_field("transcription_id", str(message.transcription_id))
        slogger.set_context_field("minute_id", str(message.minute_id))

        try:
            await self.audio_service.process_message(message)
        except AudioConversionFailedError as e:
            slogger.exception("Audio conversion failed for transcription")
            if not e.marked_failed:
                # The failure could not be recorded, so completing the message would strand the
                # transcription in AWAITING_START. Keep the current lease as retry backoff; it is
                # redelivered after the visibility timeout and eventually moved to the DLQ.
                return
        except Exception:
            # Keep the current lease as retry backoff for transient storage/database/queue errors.
            slogger.exception("Transient error in audio worker; message will be retried")
            return

        # Success, or a failure already recorded as FAILED (the user can retry from the UI):
        # either way the message is done.
        try:
            self.audio_queue_service.complete_message(receipt_handle)
        except Exception:
            # The lease may have been lost after handoff. Redelivery is safe because
            # AudioService uses a deterministic converted-recording key.
            slogger.exception("Failed to acknowledge audio queue message")

    def _heartbeat(self) -> None:
        while not self._stop_heartbeat.is_set():
            self.beat()
            self._stop_heartbeat.wait(HEARTBEAT_INTERVAL_SECONDS)

    def beat(self) -> None:
        self.heartbeat_path.touch()

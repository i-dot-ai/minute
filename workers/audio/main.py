import asyncio
import logging

from common.logger import setup_logger
from common.services.queue_services import get_queue_service
from common.settings import get_settings
from workers.audio.worker import AudioWorker
from workers.sentry import init_sentry
from workers.signal_handler import SignalHandler

logger = logging.getLogger(__name__)


def build_worker(signal_handler: SignalHandler) -> AudioWorker:
    settings = get_settings()
    transcription_queue_service = get_queue_service(
        settings.TRANSCRIPTION_QUEUE_NAME,
        settings.TRANSCRIPTION_DEADLETTER_QUEUE_NAME,
    )
    transcription_ready_queue_service = get_queue_service(
        settings.TRANSCRIPTION_READY_QUEUE_NAME,
        settings.TRANSCRIPTION_READY_DEADLETTER_QUEUE_NAME,
    )
    return AudioWorker(
        transcription_queue_service=transcription_queue_service,
        transcription_ready_queue_service=transcription_ready_queue_service,
        signal_handler=signal_handler,
    )


def main() -> None:
    setup_logger()
    init_sentry()
    logger.info("Starting audio worker")
    signal_handler = SignalHandler()
    worker = build_worker(signal_handler)
    asyncio.run(worker.run())


if __name__ == "__main__":
    main()

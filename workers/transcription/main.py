import asyncio
import logging

from common.logger import setup_logger
from common.services.queue_services import get_queue_service
from common.settings import get_settings
from workers.sentry import init_sentry
from workers.signal_handler import SignalHandler
from workers.transcription.worker import TranscriptionWorker

logger = logging.getLogger(__name__)


def build_worker(signal_handler: SignalHandler) -> TranscriptionWorker:
    settings = get_settings()
    transcription_ready_queue_service = get_queue_service(
        settings.TRANSCRIPTION_READY_QUEUE_NAME,
        settings.TRANSCRIPTION_READY_DEADLETTER_QUEUE_NAME,
    )
    llm_queue_service = get_queue_service(
        settings.LLM_QUEUE_NAME,
        settings.LLM_DEADLETTER_QUEUE_NAME,
    )
    return TranscriptionWorker(
        transcription_ready_queue_service=transcription_ready_queue_service,
        llm_queue_service=llm_queue_service,
        signal_handler=signal_handler,
    )


def main() -> None:
    setup_logger()
    init_sentry()
    settings = get_settings()
    logger.info(
        "Starting transcription worker. Transcription services: %s. "
        "LLM providers: fast=%s (%s), best=%s (%s)",
        ", ".join(settings.TRANSCRIPTION_SERVICES) or "none",
        settings.FAST_LLM_PROVIDER,
        settings.FAST_LLM_MODEL_NAME,
        settings.BEST_LLM_PROVIDER,
        settings.BEST_LLM_MODEL_NAME,
    )
    signal_handler = SignalHandler()
    worker = build_worker(signal_handler)
    asyncio.run(worker.run())


if __name__ == "__main__":
    main()

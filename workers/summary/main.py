import asyncio
import logging

from common.logger import setup_logger
from common.services.queue_services import get_queue_service
from common.settings import get_settings
from workers.sentry import init_sentry
from workers.signal_handler import SignalHandler
from workers.summary.worker import SummaryWorker

logger = logging.getLogger(__name__)


def build_worker(signal_handler: SignalHandler) -> SummaryWorker:
    settings = get_settings()
    llm_queue_service = get_queue_service(
        settings.LLM_QUEUE_NAME,
        settings.LLM_DEADLETTER_QUEUE_NAME,
    )
    return SummaryWorker(llm_queue_service=llm_queue_service, signal_handler=signal_handler)


def main() -> None:
    setup_logger()
    init_sentry()
    settings = get_settings()
    logger.info(
        "Starting summary worker. LLM providers: fast=%s (%s), best=%s (%s)",
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

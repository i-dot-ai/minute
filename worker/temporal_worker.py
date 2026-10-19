"""Temporal worker for the transcription workflow: one Worker per task queue, each with its own cap.

AI edits of minutes stay on the Ray LLM worker for now.
"""

import asyncio
import logging

from temporalio.client import Client
from temporalio.worker import Worker

from common.sentry import init_sentry
from common.services.transcription_handler_service import transcription_manager
from common.services.transcription_services.adapter import AdapterType
from common.settings import get_settings
from common.workflows.transcription import LLM_TASK_QUEUE, STT_TASK_QUEUE, TASK_QUEUE, TranscriptionWorkflow
from worker import temporal_activities

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def main() -> None:
    settings = get_settings()
    async_adapters = [
        a.name
        for a in transcription_manager.get_available_services().values()
        if a.adapter_type != AdapterType.SYNCHRONOUS
    ]
    if async_adapters:
        msg = f"Async transcription providers are not supported on Temporal yet: {async_adapters}"
        raise RuntimeError(msg)

    client = await Client.connect(settings.TEMPORAL_ADDRESS, namespace=settings.TEMPORAL_NAMESPACE)
    llm_cap = max(settings.MAX_LLM_PROCESSES, 1)
    # One Worker per task queue. Slots per queue = that resource's cap in this process;
    # extra tasks wait on the server (no timeout is consumed while waiting).
    workers = [
        Worker(
            client,
            task_queue=TASK_QUEUE,
            workflows=[TranscriptionWorkflow],
            activities=temporal_activities.WORKFLOW_QUEUE_ACTIVITIES,
        ),
        Worker(
            client,
            task_queue=STT_TASK_QUEUE,
            activities=temporal_activities.STT_ACTIVITIES,
            max_concurrent_activities=settings.STT_MAX_CONCURRENCY,
        ),
        Worker(
            client,
            task_queue=LLM_TASK_QUEUE,
            activities=temporal_activities.LLM_ACTIVITIES,
            max_concurrent_activities=llm_cap,
        ),
    ]
    logger.info(
        "Temporal worker on %s: queues %s, %s (Azure STT cap %d), %s (LLM cap %d)",
        settings.TEMPORAL_ADDRESS,
        TASK_QUEUE,
        STT_TASK_QUEUE,
        settings.STT_MAX_CONCURRENCY,
        LLM_TASK_QUEUE,
        llm_cap,
    )
    await asyncio.gather(*(w.run() for w in workers))


if __name__ == "__main__":
    init_sentry()
    asyncio.run(main())

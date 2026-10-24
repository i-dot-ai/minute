"""Temporal worker: one Worker per task queue, each with its own cap.

Queues: transcription (workflow tasks + DB writes), stt (ffmpeg + the STT provider),
llm (speakers, title, summary, minute generation and AI edits).
"""

import asyncio
import logging

from temporalio.client import Client
from temporalio.worker import Worker

from common.sentry import init_sentry
from common.settings import get_settings
from common.workflows import activities
from common.workflows.minute_version import MinuteEditWorkflow, MinuteGenerationWorkflow
from common.workflows.transcription import LLM_TASK_QUEUE, STT_TASK_QUEUE, TASK_QUEUE, TranscriptionWorkflow

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def main() -> None:
    settings = get_settings()
    client = await Client.connect(settings.TEMPORAL_ADDRESS, namespace=settings.TEMPORAL_NAMESPACE)
    llm_cap = max(settings.MAX_LLM_PROCESSES, 1)
    # One Worker per task queue. Slots per queue = that resource's cap in this process;
    # extra tasks wait on the server (no timeout is consumed while waiting).
    workers = [
        Worker(
            client,
            task_queue=TASK_QUEUE,
            workflows=[TranscriptionWorkflow, MinuteGenerationWorkflow, MinuteEditWorkflow],
            activities=activities.WORKFLOW_QUEUE_ACTIVITIES,
        ),
        Worker(
            client,
            task_queue=STT_TASK_QUEUE,
            activities=activities.STT_ACTIVITIES,
            max_concurrent_activities=settings.STT_MAX_CONCURRENCY,
        ),
        Worker(
            client,
            task_queue=LLM_TASK_QUEUE,
            activities=activities.LLM_ACTIVITIES,
            max_concurrent_activities=llm_cap,
        ),
    ]
    logger.info(
        "Temporal worker on %s: queues %s, %s (STT cap %d), %s (LLM cap %d)",
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

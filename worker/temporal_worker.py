"""Temporal worker: one Worker per task queue, each with its own cap.

Queues: transcription (workflow tasks + DB writes), stt (ffmpeg + the STT provider),
llm (speakers, title, summary, minute generation and AI edits).
"""

import asyncio
import logging
import signal

from temporalio.api.workflowservice.v1 import DescribeNamespaceRequest
from temporalio.client import Client
from temporalio.service import RPCError, RPCStatusCode
from temporalio.worker import Worker

from common.sentry import init_sentry
from common.settings import get_settings
from common.workflows import activities
from common.workflows.minute_version import MinuteEditWorkflow, MinuteGenerationWorkflow
from common.workflows.transcription import LLM_TASK_QUEUE, STT_TASK_QUEUE, TASK_QUEUE, TranscriptionWorkflow

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# The server registers its namespace a moment after it starts serving. A worker that polls before it
# exists fails fatally (NamespaceNotFound), so wait for it here rather than leaving the first poll to
# a race. This covers a cold start (schema setup, then namespace registration).
NAMESPACE_WAIT_SECONDS = 300
NAMESPACE_POLL_SECONDS = 2


async def _wait_for_namespace(client: Client, namespace: str) -> None:
    """Block until the namespace exists, or give up after NAMESPACE_WAIT_SECONDS."""
    waited = 0
    while True:
        try:
            await client.workflow_service.describe_namespace(DescribeNamespaceRequest(namespace=namespace))
            return
        except RPCError as e:
            # NOT_FOUND: the namespace isn't registered yet. UNAVAILABLE: the server isn't up yet.
            if e.status not in (RPCStatusCode.NOT_FOUND, RPCStatusCode.UNAVAILABLE):
                raise
        if waited >= NAMESPACE_WAIT_SECONDS:
            msg = f"Temporal namespace {namespace!r} did not appear within {NAMESPACE_WAIT_SECONDS}s"
            raise RuntimeError(msg)
        logger.info("Waiting for Temporal namespace %s", namespace)
        await asyncio.sleep(NAMESPACE_POLL_SECONDS)
        waited += NAMESPACE_POLL_SECONDS


async def main() -> None:
    settings = get_settings()
    client = await Client.connect(settings.TEMPORAL_ADDRESS, namespace=settings.TEMPORAL_NAMESPACE)
    await _wait_for_namespace(client, settings.TEMPORAL_NAMESPACE)

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

    stop = asyncio.Event()
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, stop.set)

    runs = [asyncio.create_task(worker.run()) for worker in workers]
    stopper = asyncio.create_task(stop.wait())
    try:
        finished, _ = await asyncio.wait([*runs, stopper], return_when=asyncio.FIRST_COMPLETED)
        if not stopper.done():
            # A worker stopped on its own; it never should while we are running. Fail loudly so the
            # process exits non-zero and the orchestrator replaces it rather than leaving a dead worker.
            for task in finished:
                if task.exception() is not None:
                    logger.error("Temporal worker failed: %s", task.exception())
            msg = "A Temporal worker exited unexpectedly"
            raise RuntimeError(msg)
    finally:
        stopper.cancel()
        # shutdown() tells the SDK to stop polling and cancel in-flight activities; a cancelled
        # attempt is reported to the server as retryable, so Temporal re-runs it on another worker.
        logger.info("Shutting down; cancelling in-flight activities (Temporal re-runs them elsewhere)")
        await asyncio.gather(*(worker.shutdown() for worker in workers))
        await asyncio.gather(*runs, return_exceptions=True)


if __name__ == "__main__":
    init_sentry()
    asyncio.run(main())

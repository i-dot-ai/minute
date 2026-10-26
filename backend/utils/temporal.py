import asyncio
from typing import Any
from uuid import UUID

from temporalio.client import Client
from temporalio.service import RPCError, RPCStatusCode

from common.settings import get_settings
from common.workflows.minute_version import MinuteEditInput, MinuteEditWorkflow, MinuteGenerationWorkflow
from common.workflows.minute_version import workflow_id as minute_version_workflow_id
from common.workflows.transcription import TASK_QUEUE, TranscriptionWorkflow, workflow_id

_client: Client | None = None
_lock = asyncio.Lock()

# On a cold start the Temporal server registers its namespace a moment after it starts serving; a
# start inside that window fails with NamespaceNotFound. Retry briefly, which is safe because a
# NOT_FOUND means nothing was created. We do not retry UNAVAILABLE: there a lost response could mean
# the workflow did start, and re-starting it would hit the id-conflict policy instead.
_NAMESPACE_RETRY_ATTEMPTS = 10
_NAMESPACE_RETRY_DELAY_SECONDS = 1.0


async def get_temporal_client() -> Client:
    global _client  # noqa: PLW0603
    async with _lock:
        if _client is None:
            settings = get_settings()
            _client = await Client.connect(settings.TEMPORAL_ADDRESS, namespace=settings.TEMPORAL_NAMESPACE)
    return _client


async def _start_workflow(workflow: Any, arg: Any, *, workflow_id: str) -> None:
    """Start a run, tolerating the namespace-not-registered-yet window on a cold deploy."""
    client = await get_temporal_client()
    for attempt in range(1, _NAMESPACE_RETRY_ATTEMPTS + 1):
        try:
            await client.start_workflow(workflow, arg, id=workflow_id, task_queue=TASK_QUEUE)
            return
        except RPCError as e:
            if e.status != RPCStatusCode.NOT_FOUND or attempt == _NAMESPACE_RETRY_ATTEMPTS:
                raise
            await asyncio.sleep(_NAMESPACE_RETRY_DELAY_SECONDS)


async def start_transcription_workflow(transcription_id: UUID, minute_id: UUID) -> None:
    """Start the run. Default conflict policy: a start while a run is still open raises."""
    await _start_workflow(TranscriptionWorkflow.run, str(minute_id), workflow_id=workflow_id(str(transcription_id)))


async def start_minute_generation_workflow(minute_version_id: UUID) -> None:
    await _start_workflow(
        MinuteGenerationWorkflow.run,
        str(minute_version_id),
        workflow_id=minute_version_workflow_id(str(minute_version_id)),
    )


async def start_minute_edit_workflow(minute_version_id: UUID, source_minute_version_id: UUID) -> None:
    params = MinuteEditInput(
        minute_version_id=str(minute_version_id), source_minute_version_id=str(source_minute_version_id)
    )
    await _start_workflow(
        MinuteEditWorkflow.run,
        params,
        workflow_id=minute_version_workflow_id(str(minute_version_id)),
    )

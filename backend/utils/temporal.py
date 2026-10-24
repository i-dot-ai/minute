import asyncio
from uuid import UUID

from temporalio.client import Client

from common.settings import get_settings
from common.workflows.minute_version import MinuteEditInput, MinuteEditWorkflow, MinuteGenerationWorkflow
from common.workflows.minute_version import workflow_id as minute_version_workflow_id
from common.workflows.transcription import TASK_QUEUE, TranscriptionWorkflow, workflow_id

_client: Client | None = None
_lock = asyncio.Lock()


async def get_temporal_client() -> Client:
    global _client  # noqa: PLW0603
    async with _lock:
        if _client is None:
            settings = get_settings()
            _client = await Client.connect(settings.TEMPORAL_ADDRESS, namespace=settings.TEMPORAL_NAMESPACE)
    return _client


async def start_transcription_workflow(transcription_id: UUID, minute_id: UUID) -> None:
    """Start the run. Default conflict policy: a start while a run is still open raises."""
    client = await get_temporal_client()
    await client.start_workflow(
        TranscriptionWorkflow.run,
        str(minute_id),
        id=workflow_id(str(transcription_id)),
        task_queue=TASK_QUEUE,
    )


async def start_minute_generation_workflow(minute_version_id: UUID) -> None:
    client = await get_temporal_client()
    await client.start_workflow(
        MinuteGenerationWorkflow.run,
        str(minute_version_id),
        id=minute_version_workflow_id(str(minute_version_id)),
        task_queue=TASK_QUEUE,
    )


async def start_minute_edit_workflow(minute_version_id: UUID, source_minute_version_id: UUID) -> None:
    client = await get_temporal_client()
    await client.start_workflow(
        MinuteEditWorkflow.run,
        MinuteEditInput(
            minute_version_id=str(minute_version_id), source_minute_version_id=str(source_minute_version_id)
        ),
        id=minute_version_workflow_id(str(minute_version_id)),
        task_queue=TASK_QUEUE,
    )

import asyncio
from uuid import UUID

from temporalio.client import Client

from common.settings import get_settings
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

"""Shared Temporal client singleton."""

import asyncio

from temporalio.client import Client

from common.settings import get_settings

_client: Client | None = None
_lock = asyncio.Lock()


async def get_temporal_client() -> Client:
    global _client  # noqa: PLW0603
    async with _lock:
        if _client is None:
            settings = get_settings()
            _client = await Client.connect(settings.TEMPORAL_ADDRESS, namespace=settings.TEMPORAL_NAMESPACE)
    return _client

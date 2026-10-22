from collections.abc import AsyncIterator
from typing import Annotated, Any

from fastapi import Depends

from common.services.storage.s3 import client


async def get_storage() -> AsyncIterator[Any]:
    """An S3 client for the duration of the request, closed once the response is sent."""
    async with client() as s3:
        yield s3


StorageDep = Annotated[Any, Depends(get_storage)]

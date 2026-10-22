import asyncio
from pathlib import Path

import s3fs

from common.settings import get_settings

settings = get_settings()


class S3Storage:
    """Async s3fs"""

    def __init__(self) -> None:
        self._fs = s3fs.S3FileSystem(
            key=settings.AWS_ACCESS_KEY_ID,
            secret=settings.AWS_SECRET_ACCESS_KEY,
            endpoint_url=settings.AWS_ENDPOINT_URL,
            client_kwargs={"region_name": settings.AWS_DEFAULT_REGION},
            asynchronous=True,
        )

    @staticmethod
    def _rpath(key: str) -> str:
        return f"{settings.AWS_S3_BUCKET}/{key}"

    async def put_file(self, path: Path, key: str) -> None:
        """Copy single file to remote"""
        await asyncio.to_thread(
            self._fs.put_file,
            lpath=str(path),
            rpath=self._rpath(key),
            mode="overwrite",
        )

    async def get_file(self, key: str, path: Path) -> None:
        """Copy single remote file to local"""
        await asyncio.to_thread(
            self._fs.get_file,
            rpath=self._rpath(key),
            lpath=str(path),
        )

    async def exists(self, key: str) -> bool:
        """Is there a file at the given path"""
        return await asyncio.to_thread(
            self._fs.exists,
            path=self._rpath(key),
        )

    async def rm(self, key: str) -> None:
        """Delete files or directories"""
        await asyncio.to_thread(
            self._fs.rm,
            path=self._rpath(key),
            recursive=False,
            maxdepth=None,
        )

    async def sign_put(self, key: str, expiry_seconds: int) -> str:
        """Return a URL the client can PUT ``key`` to."""
        return await asyncio.to_thread(
            self._fs.sign,
            self._rpath(key),
            expiration=expiry_seconds,
            client_method="put_object",
        )  # pyright: ignore[reportReturnType]

    async def sign_get(self, key: str, filename: str, expiry_seconds: int) -> str:
        """Return a URL that downloads ``key``, presented to the client as ``filename``."""
        return await asyncio.to_thread(
            self._fs.sign,
            self._rpath(key),
            expiration=expiry_seconds,
            client_method="get_object",
            ResponseContentDisposition=f"attachment; filename={filename}",
        )  # pyright: ignore[reportReturnType]

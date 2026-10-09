from pathlib import Path
from typing import Protocol


class Storage(Protocol):
    """Contract for the object storage backend."""

    async def upload(self, key: str, path: Path) -> None:
        """Store a local file under ``key``.

        :param key: Object key to store the file under.
        :param path: Local file to upload.
        """
        ...

    async def download(self, key: str, path: Path) -> None:
        """Download ``key`` to a local path.

        :param key: Object key to fetch.
        :param path: Local destination to write to.
        """
        ...

    async def generate_presigned_url_put_object(self, key: str, expiry_seconds: int) -> str:
        """Return a URL the client can PUT ``key`` to.

        :param key: Object key the upload targets.
        :param expiry_seconds: URL lifetime in seconds.
        """
        ...

    async def generate_presigned_url_get_object(self, key: str, filename: str, expiry_seconds: int) -> str:
        """Return a URL that downloads ``key``.

        :param key: Object key to download.
        :param filename: Filename presented to the client.
        :param expiry_seconds: URL lifetime in seconds.
        """
        ...

    async def check_object_exists(self, key: str) -> bool:
        """Return whether ``key`` exists.

        :param key: Object key to check.
        """
        ...

    async def delete(self, key: str) -> None:
        """Delete ``key`` if present.

        :param key: Object key to delete.
        """
        ...

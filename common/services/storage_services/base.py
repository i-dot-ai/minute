from pathlib import Path
from typing import Protocol


class StorageService(Protocol):
    name: str

    @classmethod
    async def upload(cls, key: str, path: Path) -> None: ...

    @classmethod
    async def download(cls, key: str, path: Path) -> None: ...

    @classmethod
    async def generate_presigned_url_put_object(cls, key: str, expiry_seconds: int) -> str: ...

    @classmethod
    async def generate_presigned_url_get_object(cls, key: str, filename: str, expiry_seconds: int) -> str: ...

    @classmethod
    async def check_object_exists(cls, key: str) -> bool: ...

    @classmethod
    async def delete(cls, key: str) -> None: ...

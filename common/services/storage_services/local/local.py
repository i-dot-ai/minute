import shutil
from pathlib import Path

from common.services.storage_services.base import StorageService
from common.settings import get_settings

settings = get_settings()


class LocalStorageService(StorageService):
    name = "local"

    @classmethod
    async def upload(cls, key: str, path: Path) -> None:
        storage_path = Path(settings.LOCAL_STORAGE_PATH) / key
        shutil.copy2(path, storage_path)

    @classmethod
    async def download(cls, key: str, path: Path) -> None:
        storage_path = Path(settings.LOCAL_STORAGE_PATH) / key
        shutil.copy2(storage_path, path)

    @classmethod
    async def generate_presigned_url_put_object(cls, key: str, expiry_seconds: int) -> str:  # noqa: ARG003
        return f"/api/proxy/mock_storage/uploadfile/{key}"

    @classmethod
    async def generate_presigned_url_get_object(cls, key: str, filename: str, expiry_seconds: int) -> str:  # noqa: ARG003
        return f"/api/proxy/mock_storage/static/{key}"

    @classmethod
    async def check_object_exists(cls, key: str) -> bool:
        storage_path = Path(settings.LOCAL_STORAGE_PATH) / key
        return storage_path.exists()

    @classmethod
    async def delete(cls, key: str) -> None:
        storage_path = Path(settings.LOCAL_STORAGE_PATH) / key
        storage_path.unlink(missing_ok=True)

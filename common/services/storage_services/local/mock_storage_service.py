from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles

from common.settings import get_settings

settings = get_settings()

mock_storage_app = FastAPI(title="Mock storage service")

mock_storage_app.mount("/static", StaticFiles(directory=settings.LOCAL_STORAGE_PATH), name="static")


@mock_storage_app.put("/uploadfile/{file_path:path}")
async def upload_file_to_mock_storage(file_path: str, request: Request):
    storage_path = Path(settings.LOCAL_STORAGE_PATH) / file_path
    storage_path.parent.mkdir(parents=True, exist_ok=True)
    storage_path.write_bytes(await request.body())

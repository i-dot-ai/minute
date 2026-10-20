from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.staticfiles import StaticFiles

from common.settings import get_settings

settings = get_settings()

mock_storage_app = FastAPI(title="Mock storage service")

mock_storage_app.mount("/static", StaticFiles(directory=settings.LOCAL_STORAGE_PATH), name="static")


@mock_storage_app.put("/uploadfile/{file_path:path}")
async def upload_file_to_mock_storage(file_path: str, request: Request):
    # Prevent clients to write files outside the configured storage directory
    storage_root = Path(settings.LOCAL_STORAGE_PATH).resolve()
    storage_path = (storage_root / file_path).resolve()
    try:
        storage_path.relative_to(storage_root)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid storage path") from exc
    storage_path.parent.mkdir(parents=True, exist_ok=True)
    storage_path.write_bytes(await request.body())

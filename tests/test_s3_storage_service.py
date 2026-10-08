from contextlib import asynccontextmanager
from pathlib import Path
from unittest.mock import AsyncMock

import pytest

from common.services.storage_services import s3


@pytest.mark.asyncio
async def test_upload_streams_from_disk(monkeypatch, tmp_path: Path):
    path = tmp_path / "recording.mp3"
    path.write_bytes(b"audio")
    client = AsyncMock()

    @asynccontextmanager
    async def client_context():
        yield client

    monkeypatch.setattr(s3, "_create_boto3_s3_client", client_context)
    monkeypatch.setattr(s3.settings, "DATA_S3_BUCKET", "bucket")

    await s3.S3StorageService.upload("recording.mp3", path)

    client.upload_file.assert_awaited_once_with(str(path), "bucket", "recording.mp3")

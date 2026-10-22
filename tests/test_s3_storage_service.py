from pathlib import Path
from unittest.mock import AsyncMock

import pytest
from botocore.exceptions import ClientError

from common.services.storage import s3


@pytest.mark.asyncio
async def test_upload_streams_from_disk(monkeypatch, tmp_path: Path):
    path = tmp_path / "recording.mp3"
    path.write_bytes(b"audio")
    client = AsyncMock()

    monkeypatch.setattr(s3.settings, "AWS_S3_BUCKET", "bucket")

    await s3.upload(client, "recording.mp3", path)

    client.upload_file.assert_awaited_once_with(str(path), "bucket", "recording.mp3")


@pytest.mark.asyncio
async def test_exists_is_false_when_the_key_is_missing(monkeypatch):
    client = AsyncMock()
    client.head_object.side_effect = ClientError({"Error": {"Code": "404"}}, "HeadObject")
    monkeypatch.setattr(s3.settings, "AWS_S3_BUCKET", "bucket")

    assert await s3.exists(client, "missing") is False


@pytest.mark.asyncio
async def test_exists_reraises_unexpected_errors(monkeypatch):
    client = AsyncMock()
    client.head_object.side_effect = ClientError({"Error": {"Code": "AccessDenied"}}, "HeadObject")
    monkeypatch.setattr(s3.settings, "AWS_S3_BUCKET", "bucket")

    with pytest.raises(ClientError):
        await s3.exists(client, "key")

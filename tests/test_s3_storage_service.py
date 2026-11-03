from contextlib import asynccontextmanager
from pathlib import Path
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from botocore.exceptions import ClientError

from common.services.storage_services import s3
from common.services.storage_services.local import local


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


@pytest.mark.asyncio
async def test_s3_object_size_matches_uploaded_file_and_missing_objects_fail(monkeypatch, tmp_path):
    """Uses the MiniStack service started by Compose and CI; never connects to AWS."""
    bucket = f"minute-size-test-{uuid4().hex}"
    monkeypatch.setattr(s3.settings, "ENVIRONMENT", "local")
    monkeypatch.setattr(s3.settings, "USE_MINISTACK", True)
    monkeypatch.setattr(s3.settings, "MINISTACK_URL", "http://localhost:4566")
    monkeypatch.setattr(s3.settings, "DATA_S3_BUCKET", bucket)
    monkeypatch.setattr(s3.S3StorageService, "DATA_S3_BUCKET", bucket)
    path = tmp_path / "original.wav"
    path.write_bytes(b"audio" * 247)
    async with s3._create_boto3_s3_client() as client:  # noqa: SLF001 # Use the real configured client for test setup.
        await client.create_bucket(Bucket=bucket, CreateBucketConfiguration={"LocationConstraint": "eu-west-2"})
        try:
            await s3.S3StorageService.upload("original.wav", path)
            assert await s3.S3StorageService.get_object_size("original.wav") == path.stat().st_size
            with pytest.raises(ClientError) as caught:
                await s3.S3StorageService.get_object_size("missing.wav")
            assert caught.value.response["ResponseMetadata"]["HTTPStatusCode"] == 404
        finally:
            await s3.S3StorageService.delete("original.wav")
            await client.delete_bucket(Bucket=bucket)


@pytest.mark.asyncio
async def test_local_object_size_measures_file_and_propagates_missing(monkeypatch, tmp_path):
    monkeypatch.setattr(local.settings, "LOCAL_STORAGE_PATH", str(tmp_path))
    (tmp_path / "original.wav").write_bytes(b"original")
    assert await local.LocalStorageService.get_object_size("original.wav") == len(b"original")
    with pytest.raises(FileNotFoundError):
        await local.LocalStorageService.get_object_size("missing.wav")

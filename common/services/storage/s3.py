from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

import aioboto3
from botocore.exceptions import ClientError

from common.settings import get_settings

settings = get_settings()

_NOT_FOUND = ("404", "NoSuchKey", "NotFound")


@asynccontextmanager
async def client() -> AsyncGenerator[Any]:
    """An S3 client, opened for the duration of one request or activity.

    Same shape as the DB session: the resource is created per unit of work and
    the caller owns its lifetime (``async with client() as s3``). Signed URLs carry
    the host in ``AWS_ENDPOINT_URL``, so locally that host is aliased to the endpoint
    via /etc/hosts rather than configured a second time.
    """
    session = aioboto3.Session()
    async with session.client(
        "s3",
        aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
        region_name=settings.AWS_DEFAULT_REGION,
        endpoint_url=settings.AWS_ENDPOINT_URL,
    ) as s3:  # pyright: ignore[reportGeneralTypeIssues]
        yield s3


async def upload(s3: Any, key: str, path: Path) -> None:
    """Store a local file under ``key``."""
    await s3.upload_file(str(path), settings.AWS_S3_BUCKET, key)


async def download(s3: Any, key: str, path: Path) -> None:
    """Download ``key`` to a local path."""
    await s3.download_file(settings.AWS_S3_BUCKET, key, str(path))


async def exists(s3: Any, key: str) -> bool:
    """Return whether ``key`` exists."""
    try:
        await s3.head_object(Bucket=settings.AWS_S3_BUCKET, Key=key)
    except ClientError as e:
        if e.response["Error"]["Code"] in _NOT_FOUND:
            return False
        raise
    return True


async def delete(s3: Any, key: str) -> None:
    """Delete ``key`` if present."""
    await s3.delete_object(Bucket=settings.AWS_S3_BUCKET, Key=key)


async def generate_presigned_url_put_object(s3: Any, key: str, expiry_seconds: int) -> str:
    """Return a URL the client can PUT ``key`` to."""
    return await s3.generate_presigned_url(
        ClientMethod="put_object",
        Params={"Bucket": settings.AWS_S3_BUCKET, "Key": key},
        ExpiresIn=expiry_seconds,
        HttpMethod="PUT",
    )


async def generate_presigned_url_get_object(s3: Any, key: str, filename: str, expiry_seconds: int) -> str:
    """Return a URL that downloads ``key``, presented to the client as ``filename``."""
    return await s3.generate_presigned_url(
        ClientMethod="get_object",
        Params={
            "Bucket": settings.AWS_S3_BUCKET,
            "Key": key,
            "ResponseContentDisposition": f"attachment; filename={filename}",
        },
        ExpiresIn=expiry_seconds,
        HttpMethod="GET",
    )

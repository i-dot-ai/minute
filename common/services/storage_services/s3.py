import logging
from contextlib import asynccontextmanager
from pathlib import Path

import aioboto3
import aiofiles
from botocore.exceptions import ClientError

from common.services.storage_services.base import StorageService
from common.settings import get_settings

settings = get_settings()
logger = logging.getLogger(__name__)


@asynccontextmanager
async def _create_boto3_s3_client():
    async_session = aioboto3.Session()
    async with (
        async_session.client("s3", region_name=settings.AWS_REGION) as s3,
    ):
        yield s3


class S3StorageService(StorageService):
    name = "s3"
    DATA_S3_BUCKET = settings.DATA_S3_BUCKET

    @classmethod
    async def upload(cls, key: str, path: Path) -> None:
        async with aiofiles.open(path, "rb") as file, _create_boto3_s3_client() as session:
            file_content = await file.read()

            await session.put_object(Bucket=settings.DATA_S3_BUCKET, Key=key, Body=file_content)

    @classmethod
    async def download(cls, key: str, path: Path) -> None:
        async with _create_boto3_s3_client() as session:
            await session.download_file(cls.DATA_S3_BUCKET, key, path)

    @classmethod
    async def generate_presigned_url_put_object(cls, key: str, expiry_seconds: int) -> str:
        async with _create_boto3_s3_client() as session:
            return await session.generate_presigned_url(
                ClientMethod="put_object",
                Params={
                    "Bucket": settings.DATA_S3_BUCKET,
                    "Key": key,
                },
                ExpiresIn=expiry_seconds,
                HttpMethod="PUT",
            )

    @classmethod
    async def generate_presigned_url_get_object(cls, key: str, filename: str, expiry_seconds: int) -> str:
        async with _create_boto3_s3_client() as session:
            return await session.generate_presigned_url(
                ClientMethod="get_object",
                Params={
                    "Bucket": settings.DATA_S3_BUCKET,
                    "Key": key,
                    "ResponseContentDisposition": f"attachment; filename={filename}",
                },
                ExpiresIn=expiry_seconds,
            )

    @classmethod
    async def check_object_exists(cls, key: str) -> bool:
        async with _create_boto3_s3_client() as session:
            try:
                await session.head_object(Bucket=cls.DATA_S3_BUCKET, Key=key)
            except ClientError:
                return False
            else:
                return True

    @classmethod
    async def delete_object(cls, key: str) -> None:
        async with _create_boto3_s3_client() as session:
            session.delete_object(Bucket=settings.DATA_S3_BUCKET, Key=key)

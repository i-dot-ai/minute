from contextlib import asynccontextmanager
from pathlib import Path

import aioboto3
from botocore.config import Config
from botocore.exceptions import ClientError

from common.services.storage._protocols import Storage
from common.settings import get_settings

settings = get_settings()


@asynccontextmanager
async def _session(*, from_browser: bool):
    endpoint_url = settings.AWS_ENDPOINT_URL
    if (settings.ENVIRONMENT == "local") and from_browser:
        # Endpoint the browser can resolve http://ministack => http://localhost
        endpoint_url = settings.BROWSER_AWS_ENDPOINT_URL or settings.AWS_ENDPOINT_URL

    config = None
    if settings.ENVIRONMENT == "local":
        # <bucket>.localhost => <endpoint>/<bucket>/<key>
        config = Config(s3={"addressing_style": "path"})

    _client = aioboto3.Session().client(
        "s3",
        aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
        region_name=settings.AWS_DEFAULT_REGION,
        endpoint_url=endpoint_url,
        config=config,
    )

    async with _client as session:  # pyright: ignore[reportGeneralTypeIssues]
        yield session


class S3(Storage):
    async def upload(self, key: str, path: Path) -> None:
        async with _session(from_browser=False) as sess:
            await sess.upload_file(str(path), settings.DATA_S3_BUCKET, key)

    async def download(self, key: str, path: Path) -> None:
        async with _session(from_browser=False) as sess:
            await sess.download_file(settings.DATA_S3_BUCKET, key, path)

    async def generate_presigned_url_put_object(self, key: str, expiry_seconds: int) -> str:
        params = {"Bucket": settings.DATA_S3_BUCKET, "Key": key}
        async with _session(from_browser=True) as sess:
            return await sess.generate_presigned_url(
                ClientMethod="put_object",
                Params=params,
                ExpiresIn=expiry_seconds,
                HttpMethod="PUT",
            )

    async def generate_presigned_url_get_object(self, key: str, filename: str, expiry_seconds: int) -> str:
        disposition = f"attachment; filename={filename}"
        params = {"Bucket": settings.DATA_S3_BUCKET, "Key": key}
        params["ResponseContentDisposition"] = disposition
        async with _session(from_browser=True) as sess:
            return await sess.generate_presigned_url(
                ClientMethod="get_object",
                Params=params,
                ExpiresIn=expiry_seconds,
            )

    async def check_object_exists(self, key: str) -> bool:
        async with _session(from_browser=False) as sess:
            try:
                await sess.head_object(Bucket=settings.DATA_S3_BUCKET, Key=key)
            except ClientError as e:
                error_codes = ("404", "NoSuchKey", "NotFound")
                if e.response["Error"]["Code"] in error_codes:
                    return False
                raise
        return True

    async def delete(self, key: str) -> None:
        async with _session(from_browser=False) as sess:
            await sess.delete_object(Bucket=settings.DATA_S3_BUCKET, Key=key)

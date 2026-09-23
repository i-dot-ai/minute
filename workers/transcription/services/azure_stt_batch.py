import asyncio
import datetime
import json
import logging
import uuid
from contextlib import contextmanager
from pathlib import Path

import aioboto3
import httpx
import sentry_sdk
from azure.storage.blob import BlobClient, ContainerClient, ContainerSasPermissions, generate_container_sas
from sentry_sdk.consts import SPANSTATUS
from sentry_sdk.tracing import get_span_status_from_http_code
from tenacity import retry, retry_if_exception_type, stop_after_attempt

from common.database.postgres_models import Recording
from common.services.storage_services import get_storage_service
from common.settings import get_settings
from common.types import TranscriptionJobMessageData
from workers.transcription.services._helpers import get_dialogue_entries, wait_for_retry_after
from workers.transcription.services._stt import _STT

logger = logging.getLogger(__name__)

settings = get_settings()

async_session = aioboto3.Session()
storage_service = get_storage_service(settings.STORAGE_SERVICE_NAME)


@contextmanager
def get_client():
    with ContainerClient.from_connection_string(
        settings.AZURE_BLOB_CONNECTION_STRING, settings.AZURE_TRANSCRIPTION_CONTAINER_NAME
    ) as container_client:
        yield container_client


DOMAIN = "api.cognitive.microsoft.com"
PATH = "speechtotext/transcriptions:submit"
URL = f"https://{settings.AZURE_SPEECH_REGION}.{DOMAIN}/{PATH}"
HEADERS = {
    "Content-Type": "application/json",
    "Ocp-Apim-Subscription-Key": settings.AZURE_SPEECH_KEY,
}
PARAMS = {"api-version": "2024-11-15"}

TIMEOUT_SETTINGS = httpx.Timeout(
    timeout=30.0,  # seconds
    connect=30.0,  # seconds
    read=30.0,  # seconds
    write=30.0,  # seconds
)


class AzureSTTBatch(_STT):
    """Asynchronous (batch) Azure Speech-to-Text adapter for long audio.

    Submits the recording to Azure's batch transcription API and returns a job
    handle. `check` polls the job and, once complete, downloads and returns the
    transcript; while the job is still running it returns the data unchanged so
    the caller can re-queue.
    """

    name = "azure_stt_batch"

    @classmethod
    @retry(
        retry=retry_if_exception_type((httpx.HTTPStatusError, httpx.TimeoutException)),
        wait=wait_for_retry_after(),  # honour Azure's Retry-After on 429, else exp backoff
        stop=stop_after_attempt(5),
        reraise=True,
    )
    async def start(cls, audio_file_path_or_recording: Path | Recording) -> TranscriptionJobMessageData:
        """Submit a batch transcription job to the Azure Speech-to-Text API."""
        if not isinstance(audio_file_path_or_recording, Recording):
            msg = "AzureSTTBatch.start expects a Recording"
            raise TypeError(msg)
        recording = audio_file_path_or_recording

        filename = uuid.uuid4()
        job_name = f"minute-{settings.ENVIRONMENT}-transcription-job-{filename}"
        presigned_url = await storage_service.generate_presigned_url_get_object(
            key=recording.s3_file_key,
            filename=Path(recording.s3_file_key).name,
            expiry_seconds=12 * 60 * 60,  # 12 hours
        )

        with get_client() as container_client:
            # SAS token; expiry 1 day
            sas_token = generate_container_sas(
                account_name=container_client.account_name,
                container_name=container_client.container_name,
                account_key=container_client.credential.account_key,
                permission=ContainerSasPermissions(read=True, write=True, list=True),
                expiry=datetime.datetime.now(datetime.UTC) + datetime.timedelta(days=1),
            )

            data = {
                "contentUrls": [presigned_url],
                "locale": "en-GB",
                "displayName": job_name,
                "model": None,
                "properties": {
                    "timeToLiveHours": 48,
                    "diarization": {"enabled": True},
                    "profanityFilterMode": "None",
                    "destinationContainerUrl": f"{container_client.url}?{sas_token}",
                },
            }

        with sentry_sdk.start_transaction(op="process", name="azure_stt_batch.start") as transaction:
            transaction.set_tag("file_ext", Path(recording.s3_file_key).suffix.lower().lstrip("."))
            async with httpx.AsyncClient(timeout=TIMEOUT_SETTINGS) as client:
                rsp = await client.post(URL, headers=HEADERS, json=data, params=PARAMS)
                if rsp.status_code != httpx.codes.CREATED:
                    transaction.set_tag("azure_stt_batch.status_code", rsp.status_code)
                    transaction.set_status(get_span_status_from_http_code(rsp.status_code))
                    rsp.raise_for_status()

        return TranscriptionJobMessageData(transcription_service=cls.name, job_name=rsp.json()["self"])

    @classmethod
    async def check(
        cls,
        data: TranscriptionJobMessageData,
        retry_count: int = 5,
        retry_delay: int = 5,
    ) -> TranscriptionJobMessageData:
        """Poll the batch job. Returns the transcript when done, else `data` unchanged."""
        with sentry_sdk.start_transaction(op="process", name="azure_stt_batch.check") as transaction:
            for _ in range(retry_count):
                async with httpx.AsyncClient(timeout=TIMEOUT_SETTINGS) as client:
                    try:
                        job_response = await client.get(data.job_name, headers=HEADERS, params=PARAMS)
                        job_response.raise_for_status()
                    except (httpx.HTTPStatusError, httpx.TimeoutException) as exc:
                        # Transient fault: treat as "not ready yet" and poll again
                        transaction.set_tag("azure_stt_batch.transient_error", True)
                        logger.warning("Transient error polling job status: %s", exc)
                        await asyncio.sleep(retry_delay)
                        continue

                    job_data = job_response.json()
                    job_status = job_data.get("status", None)
                    transaction.set_tag("azure_stt_batch.job_status", job_status)
                    match job_status:
                        case "Succeeded":
                            return await cls._get_results(job_data["links"]["files"], data)
                        case "Failed":
                            transaction.set_tag("azure_stt_batch.job_failed", True)
                            transaction.set_status(SPANSTATUS.INTERNAL_ERROR)
                            msg = f"Transcription job failed: {job_data.get('statusMessage', 'Unknown error')}"
                            raise ValueError(msg)
                        case None:
                            transaction.set_tag("azure_stt_batch.no_status", True)
                            transaction.set_status(SPANSTATUS.NOT_FOUND)
                            msg = f"no status in response {job_response.json()}"
                            raise ValueError(msg)
                        case _:
                            await asyncio.sleep(retry_delay)

            # Still running after exhausting the polling budget: return unchanged so the
            # caller re-queues and checks again later.
            transaction.set_tag("azure_stt_batch.still_in_progress", True)
            return data

    @classmethod
    @retry(
        retry=retry_if_exception_type((httpx.HTTPStatusError, httpx.TimeoutException)),
        wait=wait_for_retry_after(),  # honour Azure's Retry-After on 429, else exp backoff
        stop=stop_after_attempt(5),
        reraise=True,
    )
    async def _get_results(cls, files_url: str, data: TranscriptionJobMessageData) -> TranscriptionJobMessageData:
        """Download the completed transcription result and clean up provider-side blobs."""
        with sentry_sdk.start_transaction(op="process", name="azure_stt_batch.results") as transaction:
            async with httpx.AsyncClient(timeout=TIMEOUT_SETTINGS) as client:
                rsp = await client.get(files_url, headers=HEADERS, params=PARAMS)
                if rsp.status_code != httpx.codes.OK:
                    transaction.set_tag("azure_stt_batch.status_code", rsp.status_code)
                    transaction.set_status(get_span_status_from_http_code(rsp.status_code))
                    logger.error("Azure STT batch: Failed to get results: %s", rsp.status_code)
                    rsp.raise_for_status()

            result = None
            values = rsp.json().get("values")

            if not values:
                transaction.set_tag("azure_stt_batch.values_not_found", True)
                transaction.set_status(SPANSTATUS.NOT_FOUND)
                msg = "No transcription values found in response"
                raise RuntimeError(msg)

            for entry in values:
                url = entry.get("links", {}).get("contentUrl")
                if not url:
                    continue

                with get_client() as container_client:
                    blob = None
                    try:
                        blob = BlobClient.from_blob_url(url, credential=container_client.credential)
                        if entry["kind"] == "Transcription":
                            stream = blob.download_blob()
                            transcription_content = json.load(stream)
                            entries = get_dialogue_entries(transcription_content)
                            result = data.model_copy(update={"transcript": entries})
                    except Exception:
                        transaction.set_tag("azure_stt_batch.unknown_error", True)
                        transaction.set_status(SPANSTATUS.UNKNOWN_ERROR)
                        logger.exception("Failed to get transcription data")
                        continue
                    finally:
                        if blob is not None:
                            try:
                                blob.delete_blob()
                            except Exception as cleanup_error:  # noqa: BLE001
                                logger.warning("Failed to delete transcription data/report: %s", cleanup_error)
                                transaction.set_tag("azure_stt_batch.blob_cleanup_failed", True)
                                sentry_sdk.capture_exception(cleanup_error)

            if result:
                return result

            transaction.set_tag("azure_stt_batch.no_transcription_data", True)
            transaction.set_status(SPANSTATUS.NOT_FOUND)
            msg = f"no transcription data available {rsp.json()}"
            raise ValueError(msg)

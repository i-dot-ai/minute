import asyncio
import datetime
import json
import logging
import uuid
from contextlib import contextmanager
from pathlib import Path
from typing import Any

import aioboto3
import httpx
from azure.storage.blob import BlobClient, ContainerClient, ContainerSasPermissions, generate_container_sas
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from backend.app.minutes.types import TranscriptionJobMessageData
from backend.services.transcription_services.adapter import AdapterType, TranscriptionAdapter
from common.database.postgres_models import DialogueEntry, Recording
from common.services.storage_services import get_storage_service
from common.settings import get_settings

async_session = aioboto3.Session()
settings = get_settings()
logger = logging.getLogger(__name__)
storage_service = get_storage_service(settings.STORAGE_SERVICE_NAME)


@contextmanager
def get_client():
    with ContainerClient.from_connection_string(
        settings.AZURE_BLOB_CONNECTION_STRING, settings.AZURE_TRANSCRIPTION_CONTAINER_NAME
    ) as container_client:
        yield container_client


transcriptions_url = f"https://{settings.AZURE_SPEECH_REGION}.api.cognitive.microsoft.com/speechtotext/transcriptions"
submit_url = f"{transcriptions_url}:submit"
headers = {"Ocp-Apim-Subscription-Key": settings.AZURE_SPEECH_KEY, "Content-Type": "application/json"}
timeout_settings = httpx.Timeout(
    timeout=30.0,
    connect=30.0,
    read=30.0,
    write=30.0,
)
params = {"api-version": "2024-11-15"}


class AzureBatchTranscriptionAdapter(TranscriptionAdapter):
    """Adapter for AWS Transcribe service. Note, no tenacity is configured as boto3 does this automagically"""

    max_audio_length = 14400
    name = "azure_stt_batch"
    adapter_type = AdapterType.ASYNC

    @classmethod
    @retry(
        retry=retry_if_exception_type((httpx.HTTPStatusError, httpx.TimeoutException)),
        wait=wait_exponential(multiplier=1, min=4, max=10),
        stop=stop_after_attempt(5),
    )
    async def start(cls, audio_file_path_or_recording: Path | Recording) -> TranscriptionJobMessageData:
        """
        Async version of transcribe audio using Azure Speech-to-Text API
        """
        file_name = uuid.uuid4()
        job_name = f"minute-{settings.ENVIRONMENT}-transcription-job-{file_name}"
        presigned_url = await storage_service.generate_presigned_url_get_object(
            key=audio_file_path_or_recording.s3_file_key,
            filename=Path(audio_file_path_or_recording.s3_file_key).name,
            expiry_seconds=12 * 60 * 60,
        )

        with get_client() as container_client:
            sas_token = cls.get_azure_container_sas(
                container_client, ContainerSasPermissions(read=True, write=True, list=True)
            )

            data = {
                "contentUrls": [
                    presigned_url,
                ],
                "locale": "en-GB",
                "displayName": job_name,
                "model": None,
                "properties": {
                    "timeToLiveHours": 48,
                    "diarization": {
                        "enabled": True,
                    },
                    "profanityFilterMode": "None",
                    "destinationContainerUrl": f"{container_client.url}?{sas_token}",
                },
            }

        async with httpx.AsyncClient(timeout=timeout_settings) as client:
            response = await client.post(submit_url, headers=headers, json=data, params=params)
            if response.status_code != 201:  # noqa: PLR2004
                response.raise_for_status()

        return TranscriptionJobMessageData(transcription_service=cls.name, job_name=response.json()["self"])

    @classmethod
    @retry(
        retry=retry_if_exception_type((httpx.HTTPStatusError, httpx.TimeoutException)),
        wait=wait_exponential(multiplier=1, min=4, max=10),
        stop=stop_after_attempt(5),
    )
    async def get_results(cls, files_url: str, data: TranscriptionJobMessageData) -> TranscriptionJobMessageData:
        async with httpx.AsyncClient(timeout=timeout_settings) as client:
            files_response = await client.get(files_url, headers=headers, params=params)
            if files_response.status_code != 200:  # noqa: PLR2004
                files_response.raise_for_status()

            result = None
            values = files_response.json().get("values")

            if not values:
                msg = f"no values in response {files_response.json()}"
                raise ValueError(msg)

            for entry in values:
                url = entry.get("links", {}).get("contentUrl")
                try:
                    if entry["kind"] == "Transcription":
                        #   if we want details from the report, they can be accessed via:
                        # elif entry['kind'] == 'TranscriptionReport':
                        #     transcription_report_url = entry.get('links', {}).get('contentUrls', [None])[0]

                        with get_client() as container_client:
                            blob = BlobClient.from_blob_url(url, credential=container_client.credential)
                            stream = blob.download_blob()
                            transcription_content = json.load(stream)
                            result = data.model_copy(
                                update={"transcript": cls.get_dialogue_entries(transcription_content)}
                            )
                except Exception:
                    msg = "Failed to get transcription data from Azure."
                    logger.exception(msg)
                    continue
                finally:
                    # always try to delete the blob, if found
                    try:
                        if url:
                            blob = BlobClient.from_blob_url(url, credential=container_client.credential)
                            blob.delete_blob()
                    except Exception as cleanup_error:  # noqa: BLE001
                        msg = f"Failed to delete transcription data/report: {cleanup_error}"
                        logger.warning(msg)
                    else:
                        msg = f"Deleted transcription data at: {url}"
                        logger.info(msg)

            if result:
                return result
            else:
                msg = f"no transcription data available {files_response.json()}"
                raise ValueError(msg)

    @classmethod
    def get_dialogue_entries(cls, phrases: dict[str, Any]) -> list[DialogueEntry]:
        return [
            DialogueEntry(
                speaker=str(entry["speaker"]),
                text=entry["nBest"][0]["display"],
                start_time=float(entry["offsetMilliseconds"]) / 1000,
                end_time=(float(entry["offsetMilliseconds"]) + float(entry["durationMilliseconds"])) / 1000,
            )
            for entry in phrases["recognizedPhrases"]
        ]

    @classmethod
    @retry(
        retry=retry_if_exception_type((httpx.HTTPStatusError, httpx.TimeoutException)),
        wait=wait_exponential(multiplier=1, min=4, max=10),
        stop=stop_after_attempt(5),
    )
    async def check(
        cls, data: TranscriptionJobMessageData, retry_count: int = 5, retry_delay: int = 5
    ) -> TranscriptionJobMessageData:
        # Poll for completion
        for _ in range(retry_count):
            async with httpx.AsyncClient(timeout=timeout_settings) as client:
                job_response = await client.get(data.job_name, headers=headers, params=params)
                if job_response.status_code != 200:  # noqa: PLR2004
                    job_response.raise_for_status()

                job_data = job_response.json()
                job_status = job_data.get("status", None)
                match job_status:
                    case "Succeeded":
                        return await cls.get_results(job_data["links"]["files"], data)
                    case "Failed":
                        msg = f"Transcription job failed: {job_data.get('statusMessage', 'Unknown error')}"
                        raise ValueError(msg)
                    case None:
                        msg = f"no status in response {job_response.json()}"
                        raise ValueError(msg)
                    case _:
                        await asyncio.sleep(retry_delay)
        return data

    @classmethod
    def is_available(cls) -> bool:
        return bool(settings.AZURE_SPEECH_KEY and settings.AZURE_SPEECH_REGION)

    @classmethod
    def get_azure_container_sas(
        cls, container_client: ContainerClient, container_permissions: ContainerSasPermissions, expiry_time: int = 1
    ) -> str:
        start_time = datetime.datetime.now(datetime.UTC)
        expiry_time = start_time + datetime.timedelta(days=expiry_time)
        return generate_container_sas(
            account_name=container_client.account_name,
            container_name=container_client.container_name,
            account_key=container_client.credential.account_key,
            permission=container_permissions,
            expiry=expiry_time,
        )

import logging
import os
import time
from pathlib import Path
from typing import Any

import aiofiles
import httpx
import sentry_sdk
from i_dot_ai_utilities.logging.structured_logger import StructuredLogger
from i_dot_ai_utilities.logging.types.enrichment_types import ExecutionEnvironmentType
from i_dot_ai_utilities.logging.types.log_output_format import LogOutputFormat
from sentry_sdk.consts import SPANSTATUS
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from common.database.postgres_models import Recording
from common.services.exceptions import TranscriptionFailedError
from common.services.transcription_services.adapter import AdapterType, TranscriptionAdapter
from common.services.transcription_services.azure_common import convert_to_dialogue_entries
from common.settings import get_settings
from common.types import TranscriptionJobMessageData

settings = get_settings()
logger = logging.getLogger(__name__)
url = f"https://{settings.AZURE_SPEECH_REGION}.api.cognitive.microsoft.com/speechtotext/transcriptions:transcribe"
headers = {"Ocp-Apim-Subscription-Key": settings.AZURE_SPEECH_KEY}

environment = os.environ.get("ENVIRONMENT")
logger_env = ExecutionEnvironmentType.LOCAL if environment == "LOCAL" else ExecutionEnvironmentType.FARGATE
logger_fmt = LogOutputFormat.TEXT if environment == "LOCAL" else LogOutputFormat.JSON

logger = StructuredLogger(
    level=logging.INFO,
    options={
        "execution_environment": logger_env,
        "log_format": logger_fmt,
    },
)

slogger = StructuredLogger()
slogger.refresh_context()
logger.info("A thing happened", thing_id=12345, user_logged_in=True, azure=True)


class AzureSpeechAdapter(TranscriptionAdapter):
    """Adapter for Azure Speech-to-Text service."""

    max_audio_length = 7200
    name = "azure_stt_synchronous"
    adapter_type = AdapterType.SYNCHRONOUS

    @classmethod
    async def check(cls, data: TranscriptionJobMessageData) -> TranscriptionJobMessageData:
        return data

    @classmethod
    @retry(
        retry=retry_if_exception_type((httpx.HTTPStatusError, httpx.TimeoutException)),
        wait=wait_exponential(multiplier=30),  # 30, 60, 120, 240 secs
        stop=stop_after_attempt(5),
    )
    async def start(cls, audio_file_path_or_recording: Path | Recording) -> TranscriptionJobMessageData:
        """Transcribe using Azure Speech-to-Text API."""
        # Use your existing Azure transcription function
        """
        Async version of transcribe audio using Azure Speech-to-Text API
        """

        slogger.refresh_context()

        with sentry_sdk.start_transaction(op="process", name="read_file_before_azure_transcribe") as transaction:
            async with aiofiles.open(audio_file_path_or_recording, "rb") as audio_file:
                audio_content = await audio_file.read()
                files: Any = {
                    "audio": ("audio.wav", audio_content),
                    "definition": (
                        None,
                        '{"locales":["en-GB"],"diarization":{"enabled":true},"profanityFilterMode":"None"}',
                    ),
                }
            transaction.set_data("file_size", audio_file_path_or_recording.stat().st_size)
            transaction.set_data("file_type", audio_file_path_or_recording.suffix.lower())

            sentry_sdk.metrics.distribution(
                "azure_stt.file_size",
                audio_file_path_or_recording.stat().st_size,
                unit="byte",
                attributes={"adapter": cls.name},
            )

            params = {"api-version": "2024-11-15"}

            timeout_settings = httpx.Timeout(
                timeout=900.0,
                connect=900.0,
                read=900.0,
                write=900.0,
            )
        with sentry_sdk.start_transaction(op="process", name="post_file_to_azure_transcribe") as transaction:
            transaction.set_data("file_size", audio_file_path_or_recording.stat().st_size)
            async with httpx.AsyncClient(timeout=timeout_settings) as client:
                start_time = time.monotonic()
                response = await client.post(url, headers=headers, files=files, params=params)
                duration_ms = (time.monotonic() - start_time) * 1000
                transaction.set_tag("azure_stt.status_code", response.status_code)
                slogger.info("[TAG] azure_stt.status_code", azure_stt=1, status_code=response.status_code)

                sentry_sdk.metrics.count(
                    "azure_stt.requests",
                    1,
                    attributes={"adapter": cls.name, "status_code": response.status_code},
                )
                sentry_sdk.metrics.distribution(
                    "azure_stt.duration",
                    duration_ms,
                    unit="millisecond",
                    attributes={"adapter": cls.name, "status_code": response.status_code},
                )

                if response.status_code == httpx.codes.TOO_MANY_REQUESTS:
                    transaction.set_status(SPANSTATUS.RESOURCE_EXHAUSTED)
                    transaction.set_tag("azure_stt.too_many_requests", True)
                    response.raise_for_status()

                full_response = response.json()
                transaction.set_data("response", response.status_code)

                # Check for error response first
                if "code" in full_response:
                    error_message = full_response.get("message", "Unknown error occurred")
                    raise TranscriptionFailedError(error_message)
                # If no error, proceed with phrases extraction
                phrases = full_response.get("phrases")
                if not phrases:
                    error_msg = "No transcription phrases found in response"
                    raise TranscriptionFailedError(error_msg)
                return TranscriptionJobMessageData(
                    transcription_service=cls.name, transcript=convert_to_dialogue_entries(phrases)
                )

    @classmethod
    def is_available(cls) -> bool:
        return bool(settings.AZURE_SPEECH_KEY and settings.AZURE_SPEECH_REGION)

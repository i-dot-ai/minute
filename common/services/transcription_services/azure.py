import logging
from pathlib import Path
from typing import Any

import aiofiles
import httpx
import sentry_sdk
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from common.database.postgres_models import Recording
from common.services.exceptions import TranscriptionFailedError
from common.services.transcription_services.adapter import AdapterType, TranscriptionAdapter
from common.services.transcription_services.azure_common import TOO_MANY_REQUESTS, convert_to_dialogue_entries
from common.settings import get_settings
from common.types import TranscriptionJobMessageData

settings = get_settings()
logger = logging.getLogger(__name__)
url = f"https://{settings.AZURE_SPEECH_REGION}.api.cognitive.microsoft.com/speechtotext/transcriptions:transcribe"
headers = {"Ocp-Apim-Subscription-Key": settings.AZURE_SPEECH_KEY}


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
        wait=wait_exponential(multiplier=1, min=4, max=10),
        stop=stop_after_attempt(5),
    )
    async def start(cls, audio_file_path_or_recording: Path | Recording) -> TranscriptionJobMessageData:
        """Transcribe using Azure Speech-to-Text API."""
        if not settings.AZURE_SPEECH_KEY or not settings.AZURE_SPEECH_REGION:
            msg = (
                "Azure credentials not found. Please set AZURE_SPEECH_KEY and AZURE_SPEECH_REGION "
                "environment variables to run transcription evaluation."
            )
            raise ValueError(msg)

        if not isinstance(audio_file_path_or_recording, Path):
            msg = "AzureSpeechAdapter only accepts Path objects"
            raise TypeError(msg)

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
                response = await client.post(url, headers=headers, files=files, params=params)
                if response.status_code == TOO_MANY_REQUESTS:
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

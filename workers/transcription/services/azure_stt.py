import json
import logging
from pathlib import Path
from typing import Any

import aiofiles
import httpx
import sentry_sdk
from sentry_sdk.consts import SPANSTATUS
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from common.database.postgres_models import Recording
from common.settings import get_settings
from common.types import TranscriptionJobMessageData
from workers.transcription.services._helpers import get_dialogue_entries
from workers.transcription.services._stt import _STT

logger = logging.getLogger(__name__)

settings = get_settings()

DOMAIN = "api.cognitive.microsoft.com"
PATH = "speechtotext/transcriptions:transcribe"
URL = f"https://{settings.AZURE_SPEECH_REGION}.{DOMAIN}/{PATH}"
HEADERS = {"Ocp-Apim-Subscription-Key": settings.AZURE_SPEECH_KEY}
PARAMS = {"api-version": "2024-11-15"}

TIMEOUT_SETTINGS = httpx.Timeout(
    timeout=900.0,  # seconds
    connect=900.0,  # seconds
    read=900.0,  # seconds
    write=900.0,  # seconds
)


class AzureSTT(_STT):
    """Synchronous Azure Speech-to-Text adapter for short audio.

    Reads the local audio file and transcribes it in a single request, returning
    a completed job with the transcript populated.
    """

    name = "azure_stt_synchronous"

    @classmethod
    @retry(
        retry=retry_if_exception_type((httpx.HTTPStatusError, httpx.TimeoutException)),
        wait=wait_exponential(multiplier=1),  # Retry: 1, 2, 4, 8 seconds
        stop=stop_after_attempt(5),
        reraise=True,
    )
    async def start(cls, audio_file_path_or_recording: Path | Recording) -> TranscriptionJobMessageData:
        """Transcribe a local audio file using the Azure Speech-to-Text API."""
        if not isinstance(audio_file_path_or_recording, Path):
            msg = "AzureSTT.start expects a local audio file Path"
            raise TypeError(msg)
        audio_filepath = audio_file_path_or_recording
        file_size = audio_filepath.stat().st_size
        file_ext = audio_filepath.suffix.lower().lstrip(".")

        with sentry_sdk.start_transaction(op="process", name="azure_stt.file") as transaction:
            transaction.set_data("file_size", file_size)
            transaction.set_tag("file_ext", file_ext)
            async with aiofiles.open(audio_filepath, "rb") as audio_file:
                audio_content = await audio_file.read()
                definition = json.dumps({
                    "locales": ["en-GB"],
                    "diarization": {"enabled": True},
                    "profanityFilterMode": "None",
                })
                files: Any = {
                    "audio": (audio_filepath.name, audio_content),
                    "definition": (None, definition),
                }

        with sentry_sdk.start_transaction(op="process", name="azure_stt.start") as transaction:
            transaction.set_data("file_size", file_size)
            transaction.set_tag("file_ext", file_ext)
            async with httpx.AsyncClient(timeout=TIMEOUT_SETTINGS) as client:
                response = await client.post(URL, headers=HEADERS, files=files, params=PARAMS)
                transaction.set_tag("azure_stt.status_code", response.status_code)

                if response.status_code == httpx.codes.TOO_MANY_REQUESTS:
                    transaction.set_tag("azure_stt.too_many_requests", True)
                    transaction.set_status(SPANSTATUS.RESOURCE_EXHAUSTED)
                    response.raise_for_status()

                full_response = response.json()

                # Check for error response first
                if "code" in full_response:
                    error_message = full_response.get("message", "Unknown error occurred")
                    transaction.set_tag("azure_stt.unknown_error", True)
                    transaction.set_status(SPANSTATUS.UNKNOWN_ERROR)
                    raise RuntimeError(error_message)

                # If no error, proceed with phrases extraction
                if not (phrases := full_response.get("phrases")):
                    transaction.set_tag("azure_stt.phrases_not_found", True)
                    transaction.set_status(SPANSTATUS.NOT_FOUND)
                    error_msg = "No transcription phrases found in response"
                    raise RuntimeError(error_msg)

                return TranscriptionJobMessageData(
                    transcription_service=cls.name,
                    transcript=get_dialogue_entries(phrases),
                )

    @classmethod
    async def check(cls, data: TranscriptionJobMessageData) -> TranscriptionJobMessageData:
        """Synchronous transcription is already complete, so just return the data."""
        return data

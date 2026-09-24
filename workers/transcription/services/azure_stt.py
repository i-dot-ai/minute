import json
import logging
from pathlib import Path
from typing import Any

import aiofiles
import httpx
import sentry_sdk
from sentry_sdk.consts import SPANSTATUS
from tenacity import retry, retry_if_exception_type, stop_after_attempt

from common.database.postgres_models import Recording
from common.settings import get_settings
from common.types import TranscriptionJobMessageData
from workers.transcription.services._helpers import get_dialogue_entries, log_retry_after, wait_for_retry_after
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
        wait=wait_for_retry_after(),  # honour Azure's Retry-After on 429, else exp backoff
        stop=stop_after_attempt(5),
        before_sleep=log_retry_after,  # log the delay (and Azure's suggestion) before each retry
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

                # Raise on any 4xx/5xx before attempting to parse JSON. Azure error
                # responses (e.g. a 500) can have an empty or non-JSON body, which would
                # otherwise surface as a confusing JSONDecodeError. Raising here yields a
                # clear HTTPStatusError; because that type is in the retry list above,
                # transient 5xx responses are retried (honouring any Retry-After header).
                if response.is_error:
                    transaction.set_status(SPANSTATUS.UNKNOWN_ERROR)
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
                    # Azure returned success but recognised no speech (e.g. a silent or
                    # near-empty recording). This is a valid outcome, not a failure: log
                    # it and return an empty transcript so the job completes gracefully.
                    duration_ms = full_response.get("durationMilliseconds")
                    logger.warning(
                        "Azure STT recognised no speech (status=%s, durationMs=%s, keys=%s, file_size=%s, "
                        "file_ext=%s). Returning empty transcript. Response: %s",
                        response.status_code,
                        duration_ms,
                        sorted(full_response.keys()),
                        file_size,
                        file_ext,
                        json.dumps(full_response)[:2000],
                    )
                    transaction.set_data("azure_stt.duration_ms", duration_ms)
                    transaction.set_data("azure_stt.response_keys", sorted(full_response.keys()))
                    return TranscriptionJobMessageData(
                        transcription_service=cls.name,
                        transcript=[],
                    )

                return TranscriptionJobMessageData(
                    transcription_service=cls.name,
                    transcript=get_dialogue_entries(phrases),
                )

    @classmethod
    async def check(cls, data: TranscriptionJobMessageData) -> TranscriptionJobMessageData:
        """Synchronous transcription is already complete, so just return the data."""
        return data

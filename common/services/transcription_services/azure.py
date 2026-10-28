import asyncio
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import httpx
import sentry_sdk

from common.database.postgres_models import Recording
from common.services.exceptions import TranscriptionFailedError
from common.services.transcription_services.adapter import AdapterType, TranscriptionAdapter
from common.services.transcription_services.azure_common import convert_to_dialogue_entries
from common.settings import Settings, get_settings, get_structured_logger
from common.types import TranscriptionJobMessageData

settings = get_settings()
slogger = get_structured_logger()

API_PARAMS = {"api-version": "2025-10-15"}
TIMEOUT = httpx.Timeout(
    timeout=900.0,
    connect=900.0,
    read=900.0,
    write=900.0,
)


@dataclass(frozen=True)
class AzureSpeechRegion:
    region: str
    key: str

    @property
    def url(self) -> str:
        return f"https://{self.region}.api.cognitive.microsoft.com/speechtotext/transcriptions:transcribe"

    @property
    def headers(self) -> dict[str, str]:
        return {"Ocp-Apim-Subscription-Key": self.key}


def _configured_regions(settings: Settings) -> list[AzureSpeechRegion]:
    """The primary region, then each fallback, in the order to try them. Any without both a region and a key is left
    out."""
    candidates = [
        ("AZURE_SPEECH", settings.AZURE_SPEECH_REGION, settings.AZURE_SPEECH_KEY),
        ("AZURE_SPEECH_FALLBACK_1", settings.AZURE_SPEECH_FALLBACK_1_REGION, settings.AZURE_SPEECH_FALLBACK_1_KEY),
        ("AZURE_SPEECH_FALLBACK_2", settings.AZURE_SPEECH_FALLBACK_2_REGION, settings.AZURE_SPEECH_FALLBACK_2_KEY),
    ]
    regions = []
    for name, region, key in candidates:
        if region and key:
            regions.append(AzureSpeechRegion(region=region, key=key))
        else:
            slogger.warning("{name}_REGION or {name}_KEY is missing or empty, so it won't be used", name=name)
    return regions


regions = _configured_regions(settings)


class AzureSpeechAdapter(TranscriptionAdapter):
    """Adapter for Azure Speech-to-Text service."""

    max_audio_length = 17999  # Fast transcription requires audio shorter than 5 hours
    name = "azure_stt_synchronous"
    adapter_type = AdapterType.SYNCHRONOUS

    @classmethod
    async def check(cls, data: TranscriptionJobMessageData) -> TranscriptionJobMessageData:
        return data

    @classmethod
    async def start(
        cls,
        audio_file_path_or_recording: Path | Recording,
        timeout_seconds: float | None = None,
        attempt: int = 1,
        transcription_id: str | None = None,  # noqa: ARG003
    ) -> TranscriptionJobMessageData:
        """One request per Temporal attempt, rotating through configured regions on retries."""
        if not isinstance(audio_file_path_or_recording, Path):
            msg = "Synchronous transcription requires a local audio file"
            raise TypeError(msg)
        audio_file_path = audio_file_path_or_recording
        if not regions:
            msg = "No Azure speech regions are configured"
            raise TranscriptionFailedError(msg)
        region = regions[(attempt - 1) % len(regions)]
        # The caller sizes this from the audio duration; fall back to the adapter default.
        request_timeout = httpx.Timeout(timeout_seconds) if timeout_seconds else TIMEOUT

        with (
            sentry_sdk.start_transaction(op="process", name="post_file_to_azure_transcribe") as transaction,
            audio_file_path.open("rb") as audio_file,
        ):
            files: Any = {
                "audio": ("audio.wav", audio_file),
                "definition": (
                    None,
                    '{"locales":["en-GB"],"diarization":{"enabled":true},"profanityFilterMode":"None"}',
                ),
            }
            transaction.set_data("file_size", audio_file_path.stat().st_size)
            transaction.set_data("file_type", audio_file_path.suffix.lower())
            transaction.set_data("timeout_seconds", timeout_seconds)
            transaction.set_data("azure_region", region.region)
            transaction.set_data("attempt", attempt)
            slogger.info("Azure STT attempt {attempt} in {region}", attempt=attempt, region=region.region)
            async with httpx.AsyncClient(timeout=request_timeout) as client:
                start_time = time.monotonic()
                # HTTPX bounds individual I/O waits; also bound the whole request within the activity budget.
                async with asyncio.timeout(timeout_seconds or TIMEOUT.read):
                    response = await client.post(region.url, headers=region.headers, files=files, params=API_PARAMS)
                slogger.info(
                    "[TAG]",
                    tag="azure_stt",
                    num_requests=1,
                    region=region.region,
                    attempt=attempt,
                    status_code=response.status_code,
                    duration_ms=int((time.monotonic() - start_time) * 1000),
                )
                response.raise_for_status()

                full_response = response.json()
                transaction.set_data("response", response.status_code)

                # Check for error response first
                if "error" in full_response:
                    error_message = full_response["error"].get("message", "Unknown error occurred")
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

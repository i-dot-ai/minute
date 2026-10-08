import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import httpx
import sentry_sdk
from tenacity import retry, retry_if_exception, stop_after_attempt, wait_exponential

from common.database.postgres_models import Recording
from common.services.exceptions import TranscriptionFailedError
from common.services.transcription_services.adapter import AdapterType, TranscriptionAdapter
from common.services.transcription_services.azure_common import convert_to_dialogue_entries
from common.settings import Settings, get_settings, get_structured_logger
from common.types import TranscriptionJobMessageData

settings = get_settings()
slogger = get_structured_logger()

# Throttling and transient server errors mean the region can't take the request right now, so it goes to the next
# region instead. Any other error response would fail the same way everywhere, so it fails the transcription.
RETRYABLE_STATUS_CODES = {
    httpx.codes.TOO_MANY_REQUESTS,
    httpx.codes.INTERNAL_SERVER_ERROR,
    httpx.codes.BAD_GATEWAY,
    httpx.codes.SERVICE_UNAVAILABLE,
    httpx.codes.GATEWAY_TIMEOUT,
}
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


def _is_retryable(exception: BaseException) -> bool:
    if isinstance(exception, httpx.HTTPStatusError):
        return exception.response.status_code in RETRYABLE_STATUS_CODES
    return isinstance(exception, httpx.TimeoutException)


class AzureSpeechAdapter(TranscriptionAdapter):
    """Adapter for Azure Speech-to-Text service."""

    max_audio_length = 17999  # Fast transcription requires audio shorter than 5 hours
    name = "azure_stt_synchronous"
    adapter_type = AdapterType.SYNCHRONOUS

    @classmethod
    async def check(cls, data: TranscriptionJobMessageData) -> TranscriptionJobMessageData:
        return data

    @classmethod
    async def _post_with_failover(cls, client: httpx.AsyncClient, files: Any) -> tuple[httpx.Response, int]:
        """Send the request to each region in turn until one can take it. Returns the response and the index of the
        region that served it. If every region is throttled or failing, the last region's error is raised so that the
        retry decorator on start() backs off before sweeping the regions again."""
        errors: list[httpx.HTTPStatusError | httpx.TimeoutException] = []
        for index, region in enumerate(regions):
            try:
                files["audio"][1].seek(0)
                start_time = time.monotonic()
                response = await client.post(region.url, headers=region.headers, files=files, params=API_PARAMS)
                duration_ms = int((time.monotonic() - start_time) * 1000)

                slogger.info(
                    "[TAG]",
                    tag="azure_stt",
                    num_requests=1,
                    region=region.region,
                    status_code=response.status_code,
                    duration_ms=duration_ms,
                )

                # Fail over on the status code alone, because a gateway's error body may be an HTML page rather than
                # Azure's JSON.
                if response.status_code in RETRYABLE_STATUS_CODES:
                    response.raise_for_status()
            except httpx.HTTPStatusError as e:
                slogger.warning(
                    "Azure STT region {region} returned {status_code}",
                    region=region.region,
                    status_code=e.response.status_code,
                )
                errors.append(e)
            except httpx.TimeoutException as e:
                slogger.warning("Azure STT region {region} timed out", region=region.region)
                errors.append(e)
            else:
                return response, index
        raise errors[-1]

    @classmethod
    @retry(
        retry=retry_if_exception(_is_retryable),
        wait=wait_exponential(multiplier=30),  # 30, 60, 120, 240 secs between sweeps of every region
        stop=stop_after_attempt(5),
    )
    async def start(cls, audio_file_path_or_recording: Path | Recording) -> TranscriptionJobMessageData:
        """Transcribe using Azure Speech-to-Text API."""
        # Use your existing Azure transcription function
        """
        Async version of transcribe audio using Azure Speech-to-Text API
        """

        if not isinstance(audio_file_path_or_recording, Path):
            msg = "Synchronous transcription requires a local audio file"
            raise TypeError(msg)
        audio_file_path = audio_file_path_or_recording

        with (
            sentry_sdk.start_transaction(
                op="process",
                name="post_file_to_azure_transcribe",
            ) as transaction,
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
            async with httpx.AsyncClient(timeout=TIMEOUT) as client:
                response, region_index = await cls._post_with_failover(client, files)
                transaction.set_data("azure_region", regions[region_index].region)
                transaction.set_data("azure_region_failovers", region_index)

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

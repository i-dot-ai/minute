"""Azure Speech-to-Text transcription service (synchronous fast transcription).

Sends the prepared audio to Azure, failing over across configured regions on
throttling/5xx/timeout and retrying the whole sweep with exponential backoff.
"""

import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import httpx
from tenacity import retry, retry_if_exception, stop_after_attempt, wait_exponential

from common.database.postgres_models import DialogueEntry
from common.services.stt._protocols import STT, TranscriptionFailedError
from common.settings import Settings, get_settings, get_structured_logger
from common.spelling import convert_american_to_british_spelling

slogger = get_structured_logger()
settings = get_settings()

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
TIMEOUT = httpx.Timeout(timeout=900.0, connect=900.0, read=900.0, write=900.0)


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


def _configured_regions(config: Settings) -> list[AzureSpeechRegion]:
    """The primary region, then each fallback, in the order to try them. Any without both a region and a key is left
    out."""
    candidates = [
        ("AZURE_SPEECH", config.AZURE_SPEECH_REGION, config.AZURE_SPEECH_KEY),
        ("AZURE_SPEECH_FALLBACK_1", config.AZURE_SPEECH_FALLBACK_1_REGION, config.AZURE_SPEECH_FALLBACK_1_KEY),
        ("AZURE_SPEECH_FALLBACK_2", config.AZURE_SPEECH_FALLBACK_2_REGION, config.AZURE_SPEECH_FALLBACK_2_KEY),
    ]
    regions: list[AzureSpeechRegion] = []
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


def convert_to_dialogue_entries(phrases: list[dict[str, Any]]) -> list[DialogueEntry]:
    return [
        DialogueEntry(
            speaker=str(entry["speaker"]),
            text=entry["text"],
            start_time=float(entry["offsetMilliseconds"]) / 1000,
            end_time=(float(entry["offsetMilliseconds"]) + float(entry["durationMilliseconds"])) / 1000,
        )
        for entry in phrases
    ]


async def _post_with_failover(client: httpx.AsyncClient, files: Any) -> tuple[httpx.Response, int]:
    """Send the request to each region in turn until one can take it. Returns the response and the index of the
    region that served it. If every region is throttled or failing, the last region's error is raised so that the
    retry decorator on _azure_transcribe backs off before sweeping the regions again."""
    errors: list[httpx.HTTPStatusError | httpx.TimeoutException] = []
    for index, region in enumerate(regions):
        try:
            files["audio"][1].seek(0)
            start_time = time.monotonic()
            response = await client.post(region.url, headers=region.headers, files=files, params=API_PARAMS)
            duration_ms = int((time.monotonic() - start_time) * 1000)

            slogger.info(
                "Azure STT",
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


@retry(
    retry=retry_if_exception(_is_retryable),
    wait=wait_exponential(multiplier=30),  # 30, 60, 120, 240 secs between sweeps of every region
    stop=stop_after_attempt(5),
)
async def _azure_transcribe(audio_file_path: Path) -> list[DialogueEntry]:
    """Transcribe using Azure Speech-to-Text API. Worst case ~82 minutes:
    5 attempts x 900s timeout + exponential backoff."""
    with audio_file_path.open("rb") as audio_file:
        files: Any = {
            "audio": ("audio.wav", audio_file),
            "definition": (
                None,
                '{"locales":["en-GB"],"diarization":{"enabled":true},"profanityFilterMode":"None"}',
            ),
        }
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            response, region_index = await _post_with_failover(client, files)
            slogger.info(
                "Azure STT served by {region} after {failovers} failovers",
                region=regions[region_index].region,
                failovers=region_index,
            )

            full_response = response.json()
            if "error" in full_response:
                error_message = full_response["error"].get("message", "Unknown error occurred")
                raise TranscriptionFailedError(error_message)
            phrases = full_response.get("phrases")
            if not phrases:
                msg = "No transcription phrases found in response"
                raise TranscriptionFailedError(msg)
            return convert_to_dialogue_entries(phrases)


def is_transcription_available() -> bool:
    return bool(settings.AZURE_SPEECH_KEY and settings.AZURE_SPEECH_REGION)


class Azure(STT):
    async def transcribe(self, audio_file_path: Path) -> list[DialogueEntry]:
        if not is_transcription_available():
            msg = "No transcription service is configured (AZURE_SPEECH_KEY/AZURE_SPEECH_REGION missing)"
            raise TranscriptionFailedError(msg)
        slogger.info("Transcribing audio with Azure STT: {num_bytes} bytes", num_bytes=audio_file_path.stat().st_size)
        entries = await _azure_transcribe(audio_file_path)
        slogger.info("Transcription returned {num_entries} phrases", num_entries=len(entries))
        for entry in entries:
            entry["text"] = convert_american_to_british_spelling(entry["text"])
        return entries

"""Azure Speech-to-Text transcription service (synchronous fast transcription).

One call = one request to one region. The caller (Temporal's retry policy on `transcribe`)
owns retrying, and passes the 1-based `attempt` so each retry walks the configured regions in
turn. Nothing here retries or fails over, so a call's duration is bounded by `timeout_seconds`.
"""

import asyncio
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import httpx

from common.services.stt._protocols import STT, TranscriptionFailedError, TranscriptionTransientError
from common.settings import Settings, get_settings, get_structured_logger
from common.spelling import convert_american_to_british_spelling
from common.types import DialogueEntry

slogger = get_structured_logger()
settings = get_settings()

# Throttling and transient server errors mean the region can't take the request right now, so this
# attempt is retried (on the next region). Any other error response would fail the same way
# everywhere, so it fails the transcription.
RETRYABLE_STATUS_CODES = {
    httpx.codes.TOO_MANY_REQUESTS,
    httpx.codes.INTERNAL_SERVER_ERROR,
    httpx.codes.BAD_GATEWAY,
    httpx.codes.SERVICE_UNAVAILABLE,
    httpx.codes.GATEWAY_TIMEOUT,
}
API_PARAMS = {"api-version": "2025-10-15"}
DEFAULT_TIMEOUT_SECONDS = 900.0


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


def region_for(attempt: int) -> AzureSpeechRegion:
    """The region for a 1-based attempt, walking the configured regions round-robin, so Temporal's
    retries fan out across them. Raises TranscriptionFailedError if none is configured."""
    if not regions:
        msg = "No Azure STT region is configured (AZURE_SPEECH_REGION/AZURE_SPEECH_KEY missing)"
        raise TranscriptionFailedError(msg)
    return regions[(max(attempt, 1) - 1) % len(regions)]


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


async def _transcribe_region(
    audio_file_path: Path, region: AzureSpeechRegion, timeout_seconds: float
) -> list[DialogueEntry]:
    """One request to one region, bounded by `timeout_seconds` in total (upload + processing)."""
    with audio_file_path.open("rb") as audio_file:
        files: Any = {
            "audio": ("audio.wav", audio_file),
            "definition": (
                None,
                '{"locales":["en-GB"],"diarization":{"enabled":true},"profanityFilterMode":"None"}',
            ),
        }
        async with httpx.AsyncClient(timeout=httpx.Timeout(timeout_seconds)) as client:
            start_time = time.monotonic()
            try:
                async with asyncio.timeout(timeout_seconds):
                    response = await client.post(region.url, headers=region.headers, files=files, params=API_PARAMS)
            except (httpx.TransportError, TimeoutError) as e:
                msg = f"Azure STT region {region.region} unavailable: {e}"
                raise TranscriptionTransientError(msg) from e
            slogger.info(
                "Azure STT",
                region=region.region,
                status_code=response.status_code,
                duration_ms=int((time.monotonic() - start_time) * 1000),
            )

    # Fail over on the status code alone, because a gateway's error body may be an HTML page rather than Azure's JSON.
    if response.status_code in RETRYABLE_STATUS_CODES:
        msg = f"Azure STT region {region.region} returned {response.status_code}"
        raise TranscriptionTransientError(msg)

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
    async def transcribe(
        self, audio_file_path: Path, timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS, attempt: int = 1
    ) -> list[DialogueEntry]:
        if not is_transcription_available():
            msg = "No transcription service is configured (AZURE_SPEECH_KEY/AZURE_SPEECH_REGION missing)"
            raise TranscriptionFailedError(msg)
        region = region_for(attempt)
        slogger.info(
            "Transcribing audio with Azure STT region {region} (attempt {attempt}): {num_bytes} bytes",
            region=region.region,
            attempt=attempt,
            num_bytes=audio_file_path.stat().st_size,
        )
        entries = await _transcribe_region(audio_file_path, region, timeout_seconds)
        slogger.info("Transcription returned {num_entries} phrases", num_entries=len(entries))
        for entry in entries:
            entry["text"] = convert_american_to_british_spelling(entry["text"])
        return entries

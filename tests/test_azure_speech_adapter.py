"""Unit tests for AzureSpeechAdapter failing over between Azure regions.

Nothing here calls Azure. httpx.AsyncClient is swapped for a real client whose transport returns canned responses and
the audio is a small synthetic file. The adapter makes one pass over the regions per call: Temporal owns retries.
"""

from pathlib import Path
from types import SimpleNamespace

import httpx
import pytest
from structlog.testing import capture_logs

from common.services.exceptions import TranscriptionFailedError
from common.services.transcription_services import azure
from common.services.transcription_services.azure import AzureSpeechAdapter, AzureSpeechRegion, _configured_regions

PRIMARY = AzureSpeechRegion(region="uksouth", key="primary-key")
FALLBACK_1 = AzureSpeechRegion(region="westeurope", key="fallback-1-key")
FALLBACK_2 = AzureSpeechRegion(region="swedencentral", key="fallback-2-key")
ALL_REGIONS = [PRIMARY, FALLBACK_1, FALLBACK_2]

TRANSCRIBE_RESPONSE = {
    "durationMilliseconds": 2400,
    "phrases": [
        {"speaker": 1, "offsetMilliseconds": 960, "durationMilliseconds": 1440, "text": "Good morning, everyone."}
    ],
}
EXPECTED_TRANSCRIPT = [{"speaker": "1", "text": "Good morning, everyone.", "start_time": 0.96, "end_time": 2.4}]

# Captured before the fixture patches the attribute, so looping the fixture stays safe.
_REAL_ASYNC_CLIENT = httpx.AsyncClient

MISSING_REGION_WARNING = (
    "AZURE_SPEECH_FALLBACK_1_REGION or AZURE_SPEECH_FALLBACK_1_KEY is missing or empty, so it won't be used"
)


def ok() -> httpx.Response:
    return httpx.Response(200, json=TRANSCRIBE_RESPONSE)


def error(status_code: int) -> httpx.Response:
    return httpx.Response(status_code, json={"error": {"code": "Error", "message": f"HTTP {status_code}"}})


def timeout() -> httpx.TimeoutException:
    msg = "timed out"
    return httpx.ReadTimeout(msg)


class QueuedTransport(httpx.AsyncBaseTransport):
    """Returns the queued responses in order, raising any queued exception instead, and records the host and key each
    request was sent with."""

    def __init__(self, responses: list[httpx.Response | Exception]):
        self.responses = list(responses)
        self.requests: list[tuple[str, str]] = []
        self.audio_sizes: list[int] = []
        self.client_kwargs: dict = {}

    async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
        body = await request.aread()
        self.audio_sizes.append(body.count(b"\0"))
        self.requests.append((request.url.host, request.headers["Ocp-Apim-Subscription-Key"]))
        response = self.responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response


@pytest.fixture
def audio_file(tmp_path: Path) -> Path:
    path = tmp_path / "audio.mp3"
    path.write_bytes(b"\0" * 1024)
    return path


@pytest.fixture
def azure_responses(monkeypatch):
    """Configures the regions and queues Azure's responses, returning the transport so tests can check the requests."""

    def configure(
        responses: list[httpx.Response | Exception], regions: list[AzureSpeechRegion] = ALL_REGIONS
    ) -> QueuedTransport:
        transport = QueuedTransport(responses)

        def async_client(**kwargs) -> httpx.AsyncClient:
            transport.client_kwargs = kwargs
            return _REAL_ASYNC_CLIENT(transport=transport, **kwargs)

        monkeypatch.setattr(azure, "regions", regions)
        monkeypatch.setattr(azure.httpx, "AsyncClient", async_client)
        return transport

    return configure


def sent_to(region: AzureSpeechRegion) -> tuple[str, str]:
    return (f"{region.region}.api.cognitive.microsoft.com", region.key)


@pytest.mark.asyncio
async def test_transcribes(azure_responses, audio_file):
    cases = [
        ("primary serves the request", [ok()], [PRIMARY]),
        ("throttled primary fails over", [error(429), ok()], [PRIMARY, FALLBACK_1]),
        ("server errors fail over", [error(500), error(503), ok()], ALL_REGIONS),
        ("timeout fails over", [timeout(), ok()], [PRIMARY, FALLBACK_1]),
    ]
    for name, responses, expected_requests in cases:
        transport = azure_responses(responses, ALL_REGIONS)

        result = await AzureSpeechAdapter.start(audio_file)

        assert result.transcript == EXPECTED_TRANSCRIPT, name
        assert transport.requests == [sent_to(region) for region in expected_requests], name
        assert transport.audio_sizes == [1024] * len(expected_requests), name


@pytest.mark.asyncio
async def test_failure_sweeps_regions_once(azure_responses, audio_file):
    # One sweep of the regions per call: retrying is Temporal's job, not the adapter's.
    transport = azure_responses([error(429) for _ in range(len(ALL_REGIONS))])

    with pytest.raises(httpx.HTTPStatusError):
        await AzureSpeechAdapter.start(audio_file)

    assert transport.requests == [sent_to(region) for region in ALL_REGIONS]

    # A 4xx (bad request) is not worth failing over.
    transport = azure_responses([error(400)])

    with pytest.raises(TranscriptionFailedError, match="HTTP 400"):
        await AzureSpeechAdapter.start(audio_file)

    assert transport.requests == [sent_to(PRIMARY)]


def region_settings(**overrides: str | None) -> SimpleNamespace:
    """Settings with the primary and both fallback regions configured, apart from any overrides."""
    values = {
        "AZURE_SPEECH_REGION": PRIMARY.region,
        "AZURE_SPEECH_KEY": PRIMARY.key,
        "AZURE_SPEECH_FALLBACK_1_REGION": FALLBACK_1.region,
        "AZURE_SPEECH_FALLBACK_1_KEY": FALLBACK_1.key,
        "AZURE_SPEECH_FALLBACK_2_REGION": FALLBACK_2.region,
        "AZURE_SPEECH_FALLBACK_2_KEY": FALLBACK_2.key,
    }
    return SimpleNamespace(**(values | overrides))


def test_configured_regions_are_primary_then_fallbacks_in_order():
    assert _configured_regions(region_settings()) == ALL_REGIONS


def test_configured_regions_warns_about_and_leaves_out_a_missing_or_empty_region_or_key():
    for region, key in (
        (FALLBACK_1.region, None),
        (None, FALLBACK_1.key),
        (FALLBACK_1.region, ""),
        ("", FALLBACK_1.key),
    ):
        settings = region_settings(AZURE_SPEECH_FALLBACK_1_REGION=region, AZURE_SPEECH_FALLBACK_1_KEY=key)

        with capture_logs() as logs:
            assert _configured_regions(settings) == [PRIMARY, FALLBACK_2]

        assert [(log["log_level"], log["event"]) for log in logs] == [("warning", MISSING_REGION_WARNING)]


@pytest.mark.asyncio
async def test_start_uses_the_callers_timeout_budget(azure_responses, audio_file):
    """The workflow's duration-based budget reaches the HTTP client."""
    transport = azure_responses([ok()])
    await AzureSpeechAdapter.start(audio_file, timeout_seconds=123.5)
    assert transport.client_kwargs["timeout"].read == 123.5


@pytest.mark.asyncio
async def test_start_falls_back_to_the_default_timeout(azure_responses, audio_file):
    transport = azure_responses([ok()])
    await AzureSpeechAdapter.start(audio_file)
    assert transport.client_kwargs["timeout"].read == azure.TIMEOUT.read

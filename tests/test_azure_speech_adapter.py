"""Unit tests for Azure STT: one request per call, on the region picked from the attempt number.

Nothing here calls Azure. httpx.AsyncClient is swapped for a real client whose transport returns
canned responses and the audio is a small synthetic file. Retrying across regions is Temporal's
job, so a failed request raises TranscriptionTransientError rather than failing over in-process.
"""

import asyncio
from pathlib import Path
from types import SimpleNamespace

import httpx
import pytest
from structlog.testing import capture_logs

from common.services.stt import TranscriptionFailedError, TranscriptionTransientError, azure
from common.services.stt.azure import Azure, AzureSpeechRegion, _configured_regions, region_for

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

    async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
        body = await request.aread()
        self.audio_sizes.append(body.count(b"\0"))
        self.requests.append((request.url.host, request.headers["Ocp-Apim-Subscription-Key"]))
        response = self.responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response


class HangingTransport(httpx.AsyncBaseTransport):
    """Accepts the request and never answers (httpx's own timeouts don't fire)."""

    async def handle_async_request(self, request: httpx.Request) -> httpx.Response:  # noqa: ARG002
        await asyncio.sleep(3600)
        return ok()


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
        real_async_client = httpx.AsyncClient

        def async_client(**kwargs) -> httpx.AsyncClient:
            return real_async_client(transport=transport, **kwargs)

        monkeypatch.setattr(azure, "regions", regions)
        monkeypatch.setattr(azure.httpx, "AsyncClient", async_client)
        return transport

    return configure


def sent_to(region: AzureSpeechRegion) -> tuple[str, str]:
    return (f"{region.region}.api.cognitive.microsoft.com", region.key)


@pytest.mark.parametrize(
    ("attempt", "expected"),
    [
        pytest.param(1, PRIMARY, id="attempt 1 -> primary region"),
        pytest.param(2, FALLBACK_1, id="attempt 2 -> fallback 1"),
        pytest.param(3, FALLBACK_2, id="attempt 3 -> fallback 2"),
        pytest.param(4, PRIMARY, id="attempt 4 wraps back to the primary"),
    ],
)
def test_region_rotates_with_the_attempt(monkeypatch, attempt, expected):
    monkeypatch.setattr(azure, "regions", ALL_REGIONS)
    assert region_for(attempt) == expected


def test_region_for_without_any_configured_region_raises(monkeypatch):
    monkeypatch.setattr(azure, "regions", [])
    with pytest.raises(TranscriptionFailedError, match="No Azure STT region is configured"):
        region_for(1)


@pytest.mark.asyncio
async def test_transcribes_on_the_attempts_region(azure_responses, audio_file):
    transport = azure_responses([ok()])

    result = await Azure().transcribe(audio_file, attempt=2)

    assert result == EXPECTED_TRANSCRIPT
    assert transport.requests == [sent_to(FALLBACK_1)]  # one request, to that attempt's region
    assert transport.audio_sizes == [1024]


@pytest.mark.parametrize(
    ("response", "expected_error"),
    [
        pytest.param(error(429), TranscriptionTransientError, id="throttled"),
        pytest.param(error(503), TranscriptionTransientError, id="service unavailable"),
        pytest.param(timeout(), TranscriptionTransientError, id="read timeout"),
        pytest.param(error(400), TranscriptionFailedError, id="bad request is not retried"),
        pytest.param(httpx.ConnectError("no route"), TranscriptionTransientError, id="network error"),
    ],
)
@pytest.mark.asyncio
async def test_one_request_then_the_matching_error(azure_responses, audio_file, response, expected_error):
    transport = azure_responses([response])

    with pytest.raises(expected_error):
        await Azure().transcribe(audio_file, attempt=1)

    assert transport.requests == [sent_to(PRIMARY)]  # one request: no in-process failover


@pytest.mark.asyncio
async def test_a_hung_region_raises_transient_within_the_timeout(monkeypatch, audio_file):
    real_async_client = httpx.AsyncClient
    monkeypatch.setattr(azure, "regions", [PRIMARY])
    monkeypatch.setattr(azure.httpx, "AsyncClient", lambda **kw: real_async_client(transport=HangingTransport(), **kw))

    with pytest.raises(TranscriptionTransientError, match="unavailable"):
        await asyncio.wait_for(Azure().transcribe(audio_file, timeout_seconds=0.2), timeout=5)


@pytest.mark.asyncio
async def test_transcribe_requires_a_configured_service(monkeypatch):
    monkeypatch.setattr(azure.settings, "AZURE_SPEECH_KEY", None)
    with pytest.raises(TranscriptionFailedError, match="No transcription service is configured"):
        await Azure().transcribe(Path("whatever.mp3"))


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
    assert _configured_regions(region_settings()) == ALL_REGIONS  # pyright: ignore[reportArgumentType]


@pytest.mark.parametrize(
    ("region", "key"),
    [
        (FALLBACK_1.region, None),
        (None, FALLBACK_1.key),
        (FALLBACK_1.region, ""),
        ("", FALLBACK_1.key),
    ],
)
def test_configured_regions_warns_about_and_leaves_out_a_missing_or_empty_region_or_key(region, key):
    settings = region_settings(AZURE_SPEECH_FALLBACK_1_REGION=region, AZURE_SPEECH_FALLBACK_1_KEY=key)

    with capture_logs() as logs:
        assert _configured_regions(settings) == [PRIMARY, FALLBACK_2]  # pyright: ignore[reportArgumentType]

    assert [(log["log_level"], log["event"]) for log in logs] == [
        (
            "warning",
            "AZURE_SPEECH_FALLBACK_1_REGION or AZURE_SPEECH_FALLBACK_1_KEY is missing or empty, so it won't be used",
        )
    ]

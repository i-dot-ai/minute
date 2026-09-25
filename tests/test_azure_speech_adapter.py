"""Unit tests for AzureSpeechAdapter failing over between Azure regions.

Nothing here calls Azure. httpx.AsyncClient is swapped for a real client whose transport returns canned responses, the
audio is a small synthetic file, and tenacity's sleep between retries returns immediately.
"""

from pathlib import Path
from types import SimpleNamespace

import httpx
import pytest
from structlog.testing import capture_logs
from tenacity import RetryError

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


def ok() -> httpx.Response:
    return httpx.Response(200, json=TRANSCRIBE_RESPONSE)


def error(status_code: int) -> httpx.Response:
    return httpx.Response(status_code, json={"code": "Error", "message": f"HTTP {status_code}"})


def timeout() -> httpx.TimeoutException:
    msg = "timed out"
    return httpx.ReadTimeout(msg)


class QueuedTransport(httpx.AsyncBaseTransport):
    """Returns the queued responses in order, raising any queued exception instead, and records the host and key each
    request was sent with."""

    def __init__(self, responses: list[httpx.Response | Exception]):
        self.responses = list(responses)
        self.requests: list[tuple[str, str]] = []

    async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
        await request.aread()
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


@pytest.fixture(autouse=True)
def backoffs(monkeypatch) -> list[float]:
    """Stops start() from actually waiting between retries in every test, and records each wait for the tests that
    check the backoff."""
    waits: list[float] = []

    async def record_sleep(seconds: float) -> None:
        waits.append(seconds)

    monkeypatch.setattr(AzureSpeechAdapter.start.retry, "sleep", record_sleep)
    return waits


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
    ("responses", "regions", "expected_requests", "expected_backoffs"),
    [
        pytest.param([ok()], ALL_REGIONS, [PRIMARY], 0, id="primary serves the request"),
        pytest.param([error(429), ok()], ALL_REGIONS, [PRIMARY, FALLBACK_1], 0, id="throttled primary fails over"),
        pytest.param([error(500), error(503), ok()], ALL_REGIONS, ALL_REGIONS, 0, id="server errors fail over"),
        pytest.param([timeout(), ok()], ALL_REGIONS, [PRIMARY, FALLBACK_1], 0, id="timeout fails over"),
        pytest.param(
            [error(429), error(429), error(429), ok()],
            ALL_REGIONS,
            [*ALL_REGIONS, PRIMARY],
            1,
            id="backs off only after every region fails",
        ),
        pytest.param([error(429), error(429), ok()], [PRIMARY], [PRIMARY] * 3, 2, id="single region backs off"),
    ],
)
@pytest.mark.asyncio
async def test_transcribes(
    azure_responses, audio_file, backoffs, responses, regions, expected_requests, expected_backoffs
):
    transport = azure_responses(responses, regions)

    result = await AzureSpeechAdapter.start(audio_file)

    assert result.transcript == EXPECTED_TRANSCRIPT
    assert transport.requests == [sent_to(region) for region in expected_requests]
    assert len(backoffs) == expected_backoffs


@pytest.mark.asyncio
async def test_gives_up_after_five_sweeps_of_every_region(azure_responses, audio_file, backoffs):
    transport = azure_responses([error(429) for _ in range(15)])

    with pytest.raises(RetryError):
        await AzureSpeechAdapter.start(audio_file)

    assert len(transport.requests) == 15
    assert len(backoffs) == 4


@pytest.mark.asyncio
async def test_client_error_fails_without_trying_other_regions(azure_responses, audio_file, backoffs):
    transport = azure_responses([error(400)])

    with pytest.raises(TranscriptionFailedError, match="HTTP 400"):
        await AzureSpeechAdapter.start(audio_file)

    assert transport.requests == [sent_to(PRIMARY)]
    assert backoffs == []


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
        assert _configured_regions(settings) == [PRIMARY, FALLBACK_2]

    assert [(log["log_level"], log["event"]) for log in logs] == [
        (
            "warning",
            "AZURE_SPEECH_FALLBACK_1_REGION or AZURE_SPEECH_FALLBACK_1_KEY is missing or empty, so it won't be used",
        )
    ]

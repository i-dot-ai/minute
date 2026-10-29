"""Unit tests for AzureSpeechAdapter making one request per Temporal attempt.

Nothing here calls Azure. httpx.AsyncClient is swapped for a real client whose transport returns canned responses and
the audio is a small synthetic file. Temporal retries rotate through the configured regions.
"""

import asyncio
from pathlib import Path
from types import SimpleNamespace

import httpx
import pytest
from structlog.testing import capture_logs
from temporalio.testing import WorkflowEnvironment

from common.database.postgres_models import JobStatus
from common.services.transcription_services import azure
from common.services.transcription_services.azure import AzureSpeechAdapter, AzureSpeechRegion, _configured_regions
from common.workflows import transcription as wf
from common.workflows.activities import _shared, transcribe
from tests.test_temporal_transcription_workflow import TRANSCRIPTION_ID, _activities, _workers

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
    for regions in (ALL_REGIONS, [PRIMARY, FALLBACK_2], [PRIMARY]):
        for attempt in range(1, 5):
            transport = azure_responses([ok()], regions)
            result = await AzureSpeechAdapter.start(audio_file, attempt=attempt)
            assert result.transcript == EXPECTED_TRANSCRIPT
            assert transport.requests == [sent_to(regions[(attempt - 1) % len(regions)])]
            assert transport.audio_sizes == [1024]


@pytest.mark.asyncio
async def test_failure_never_tries_a_second_region_in_the_same_attempt(azure_responses, audio_file):
    for response in (error(400), error(401), error(429), error(503), timeout()):
        transport = azure_responses([response, ok()])
        expected_error = httpx.TimeoutException if isinstance(response, Exception) else httpx.HTTPStatusError
        with pytest.raises(expected_error):
            await AzureSpeechAdapter.start(audio_file)
        assert transport.requests == [sent_to(PRIMARY)]


@pytest.mark.asyncio
async def test_whole_request_is_bounded_by_the_provider_budget(monkeypatch, audio_file):
    async def _hang(*_args, **_kwargs):
        await asyncio.Event().wait()

    monkeypatch.setattr(azure.httpx.AsyncClient, "post", _hang)
    with pytest.raises(TimeoutError):
        await AzureSpeechAdapter.start(audio_file, timeout_seconds=0.01)


@pytest.mark.asyncio
async def test_temporal_retries_use_distinct_regions(monkeypatch, azure_responses, audio_file):
    transport = azure_responses([timeout(), error(503), ok()])
    row = SimpleNamespace(id=TRANSCRIPTION_ID, status=JobStatus.IN_PROGRESS, dialogue_entries=None)
    monkeypatch.setattr(_shared, "load", lambda *_args: row)
    monkeypatch.setattr(_shared, "update_in_progress", lambda *_args, **_kwargs: True)
    monkeypatch.setattr(transcribe, "claim_job", lambda *_args: True)

    async def _provider(transcription, timeout_seconds, attempt):  # noqa: ARG001
        return await AzureSpeechAdapter.start(audio_file, timeout_seconds=timeout_seconds, attempt=attempt)

    monkeypatch.setattr(transcribe.transcription_manager, "perform_transcription_steps", _provider)
    by_queue = _activities([])
    by_queue[wf.STT_TASK_QUEUE] = [by_queue[wf.STT_TASK_QUEUE][0], transcribe.transcribe]
    async with await WorkflowEnvironment.start_time_skipping() as env:
        workers = _workers(env.client, by_queue)
        async with workers[0], workers[1], workers[2]:
            outcome = await env.client.execute_workflow(
                wf.TranscriptionWorkflow.run,
                "00000000-0000-0000-0000-000000000001",
                id="region-retries",
                task_queue=wf.TASK_QUEUE,
            )
    assert transport.requests == [sent_to(region) for region in ALL_REGIONS]
    assert outcome[wf.SUMMARISE] == "ok"


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

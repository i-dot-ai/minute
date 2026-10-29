"""Branch tests for the transcription activities: how each maps outcomes to Temporal results.

Collaborators are patched; ActivityEnvironment runs each activity in-process (no server, no DB).
"""

import uuid
from dataclasses import replace
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import httpx
import pytest
from sqlalchemy.exc import OperationalError
from temporalio.exceptions import ApplicationError
from temporalio.testing import ActivityEnvironment

from common.database.postgres_models import JobStatus
from common.services.exceptions import TranscriptionFailedError
from common.services.minute_handler_service import (
    MinuteGenerationFailedError,
    MinuteGenerationTransientError,
    MinuteHandlerService,
)
from common.services.transcription_handler_service import TranscriptionHandlerService
from common.workflows import minute_version as minute_wf
from common.workflows import transcription as wf
from common.workflows.activities import (
    _shared,
    complete_transcription,
    edit_minute,
    fail_minute,
    fail_transcription,
    generate_minute,
    generate_title,
    identify_speakers,
    prepare_audio,
    summarise,
    transcribe,
)

MINUTE_ID = uuid.uuid4()
TRANSCRIPTION_ID = uuid.uuid4()
ENTRIES = [{"speaker": "A", "text": "hi", "start_time": 0.0, "end_time": 1.0}]
TRANSCRIBE_INPUT = wf.TranscribeInput(minute_id=str(MINUTE_ID), stt_timeout_seconds=60)


def _row(status=JobStatus.IN_PROGRESS, entries=ENTRIES, title=None):
    return SimpleNamespace(
        id=TRANSCRIPTION_ID, user_id=uuid.uuid4(), status=status, dialogue_entries=entries, title=title
    )


async def _run(fn, arg):
    return await ActivityEnvironment().run(fn, arg)


@pytest.fixture
def writes(monkeypatch):
    """Record IN_PROGRESS-guarded writes; returns True (row was IN_PROGRESS)."""
    calls: list = []

    def _update(tid, **values):
        calls.append((tid, values))
        return True

    def _set_title(tid, title):
        calls.append((tid, {"title": title}))
        return True

    monkeypatch.setattr(_shared, "update_in_progress", _update)
    monkeypatch.setattr(_shared, "set_title_if_empty", _set_title)
    monkeypatch.setattr(
        _shared,
        "mark_failed",
        lambda row, error: _update(row.id, status=JobStatus.FAILED, error=f"Transcription failed: {error}"),
    )
    monkeypatch.setattr(_shared, "capture_event", lambda *_a, **_k: None)
    return calls


def _patch_row(monkeypatch, row):
    """Keep the real status guards; only replace the database lookup."""
    monkeypatch.setattr(_shared, "get_row", lambda _tid: row)


def _patch_load(monkeypatch, row):
    """Patch the minute -> transcription lookup (fail_transcription reads it by minute id)."""
    monkeypatch.setattr(_shared, "load", lambda _minute_id: row)


# --- prepare_audio ---


@pytest.mark.asyncio
async def test_prepare_audio_reports_duration(monkeypatch):
    audio = wf.PreparedAudio(duration_seconds=7200.0)
    monkeypatch.setattr(prepare_audio, "_prepare_audio", AsyncMock(return_value=audio))
    assert await _run(prepare_audio.prepare_audio, str(MINUTE_ID)) == audio


@pytest.mark.asyncio
async def test_prepare_audio_bad_audio_is_non_retryable(monkeypatch):
    # Bad audio is permanent; a moved-on row is transient and should be retried.
    for raises, non_retryable in (
        (TranscriptionFailedError("no audio stream"), True),
        (_shared.TranscriptionTransientError("row moved on"), False),
    ):
        monkeypatch.setattr(prepare_audio, "_prepare_audio", AsyncMock(side_effect=raises))
        with pytest.raises(ApplicationError) as e:
            await _run(prepare_audio.prepare_audio, str(MINUTE_ID))
        assert e.value.non_retryable is non_retryable


# --- transcribe ---


@pytest.mark.asyncio
async def test_transcribe_returns_id(monkeypatch):
    step = AsyncMock(return_value=str(TRANSCRIPTION_ID))
    monkeypatch.setattr(transcribe, "_transcribe", step)
    assert await _run(transcribe.transcribe, TRANSCRIBE_INPUT) == str(TRANSCRIPTION_ID)
    step.assert_awaited_once_with(TRANSCRIBE_INPUT)


@pytest.mark.asyncio
async def test_transcribe_error_mapping(monkeypatch):
    # Provider unavailability is transient; a handled failure is permanent.
    for raises, non_retryable in (
        (_shared.TranscriptionTransientError("provider 429"), False),
        (TranscriptionFailedError("azure said no"), True),
    ):
        monkeypatch.setattr(transcribe, "_transcribe", AsyncMock(side_effect=raises))
        with pytest.raises(ApplicationError) as e:
            await _run(transcribe.transcribe, TRANSCRIBE_INPUT)
        assert e.value.non_retryable is non_retryable


# --- fail_transcription ---


@pytest.mark.asyncio
async def test_fail_transcription_marks_in_progress_row_failed(monkeypatch, writes):
    _patch_load(monkeypatch, _row())
    params = wf.FailTranscriptionInput(minute_id=str(MINUTE_ID), error="retries exhausted")
    await _run(fail_transcription.fail_transcription, params)
    assert writes == [
        (TRANSCRIPTION_ID, {"status": JobStatus.FAILED, "error": "Transcription failed: retries exhausted"})
    ]


@pytest.mark.asyncio
async def test_fail_transcription_ignores_deleted_row(monkeypatch, writes):
    monkeypatch.setattr(_shared, "load", Mock(side_effect=TranscriptionFailedError))
    params = wf.FailTranscriptionInput(minute_id=str(MINUTE_ID), error="x")
    await _run(fail_transcription.fail_transcription, params)
    assert writes == []


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "step", [prepare_audio.prepare_audio, transcribe.transcribe, fail_transcription.fail_transcription]
)
async def test_database_read_errors_reach_temporal_instead_of_being_treated_as_deleted(monkeypatch, step):
    error = OperationalError("SELECT", None, ConnectionError("database unavailable"))

    monkeypatch.setattr(TranscriptionHandlerService, "get_transcription_from_minute_id", Mock(side_effect=error))
    arg = {
        prepare_audio.prepare_audio: str(MINUTE_ID),
        transcribe.transcribe: TRANSCRIBE_INPUT,
        fail_transcription.fail_transcription: wf.FailTranscriptionInput(str(MINUTE_ID), "retries exhausted"),
    }[step]
    with pytest.raises(OperationalError) as caught:
        await _run(step, arg)
    assert caught.value is error


@pytest.mark.asyncio
@pytest.mark.parametrize("step", [generate_minute.generate_minute, edit_minute.edit_minute])
async def test_minute_database_read_errors_are_retryable(monkeypatch, step):
    error = OperationalError("SELECT", None, ConnectionError("database unavailable"))
    monkeypatch.setattr(MinuteHandlerService, "get_minute_version", AsyncMock(side_effect=error))
    arg = (
        str(MINUTE_ID)
        if step == generate_minute.generate_minute
        else minute_wf.MinuteEditInput(str(MINUTE_ID), str(TRANSCRIPTION_ID))
    )
    with pytest.raises(ApplicationError) as caught:
        await _run(step, arg)
    assert not caught.value.non_retryable


@pytest.mark.asyncio
async def test_transcribe_passes_temporal_attempt_to_provider(monkeypatch, writes):
    row = _row(entries=None)
    _patch_load(monkeypatch, row)
    monkeypatch.setattr(transcribe, "claim_job", lambda *_args: True)
    provider = AsyncMock(return_value=SimpleNamespace(transcript=ENTRIES))
    monkeypatch.setattr(transcribe.transcription_manager, "perform_transcription_steps", provider)
    env = ActivityEnvironment()
    env.info = replace(env.info, attempt=3)
    assert await env.run(transcribe.transcribe, TRANSCRIBE_INPUT) == str(TRANSCRIPTION_ID)
    provider.assert_awaited_once_with(transcription=row, timeout_seconds=60, attempt=3)
    assert writes == [(TRANSCRIPTION_ID, {"dialogue_entries": ENTRIES})]


# --- identify_speakers / generate_title ---


@pytest.mark.asyncio
async def test_identify_speakers_saves_named_entries(monkeypatch, writes):
    named = [{**ENTRIES[0], "speaker": "Alice"}]
    _patch_row(monkeypatch, _row())
    monkeypatch.setattr(TranscriptionHandlerService, "identify_speakers", AsyncMock(return_value=named))
    await _run(identify_speakers.identify_speakers, str(TRANSCRIPTION_ID))
    assert writes == [(TRANSCRIPTION_ID, {"dialogue_entries": named})]


@pytest.mark.asyncio
async def test_generate_title_saves_title(monkeypatch, writes):
    llm = AsyncMock(return_value="Weekly sync")
    _patch_row(monkeypatch, _row())
    monkeypatch.setattr(generate_title, "generate_meeting_title", llm)
    await _run(generate_title.generate_title, str(TRANSCRIPTION_ID))
    llm.assert_awaited_once_with(transcript=ENTRIES)
    assert writes == [(TRANSCRIPTION_ID, {"title": "Weekly sync"})]


@pytest.mark.asyncio
async def test_post_processing_skips_rows_no_longer_in_progress(monkeypatch, writes):
    for fn in (identify_speakers.identify_speakers, generate_title.generate_title):
        for row in (None, _row(JobStatus.FAILED), _row(JobStatus.COMPLETED)):
            writes.clear()
            _patch_row(monkeypatch, row)
            await _run(fn, str(TRANSCRIPTION_ID))
            assert writes == [], (fn.__name__, row)


@pytest.mark.asyncio
async def test_title_llm_error_propagates_for_temporal_to_retry(monkeypatch, writes):
    _patch_row(monkeypatch, _row())
    monkeypatch.setattr(generate_title, "generate_meeting_title", AsyncMock(side_effect=RuntimeError("llm down")))
    with pytest.raises(RuntimeError):
        await _run(generate_title.generate_title, str(TRANSCRIPTION_ID))
    assert writes == []


@pytest.mark.asyncio
async def test_speaker_provider_error_propagates_without_changing_entries(monkeypatch, writes):
    _patch_row(monkeypatch, _row())
    bot = SimpleNamespace(structured_chat=AsyncMock(side_effect=httpx.ReadTimeout("LLM temporarily unavailable")))
    monkeypatch.setattr("common.audio.generate_speaker_predictions.create_default_chatbot", lambda *_args: bot)
    with pytest.raises(httpx.ReadTimeout):
        await _run(identify_speakers.identify_speakers, str(TRANSCRIPTION_ID))
    assert writes == []
    assert ENTRIES[0]["speaker"] == "A"
    bot.structured_chat.assert_awaited_once()


@pytest.mark.asyncio
async def test_generate_title_skips_existing_title(monkeypatch, writes):
    _patch_row(monkeypatch, _row(title="User title"))
    llm = AsyncMock()
    monkeypatch.setattr(generate_title, "generate_meeting_title", llm)
    await _run(generate_title.generate_title, str(TRANSCRIPTION_ID))
    llm.assert_not_awaited()
    assert writes == []


# --- complete_transcription ---


@pytest.mark.asyncio
async def test_complete_transcription(monkeypatch):
    for applied, row, expected in (
        (True, _row(), True),
        (False, _row(JobStatus.COMPLETED), True),  # retry after an earlier attempt already completed it
        (False, _row(JobStatus.FAILED), False),
        (False, None, False),  # deleted
    ):
        monkeypatch.setattr(_shared, "update_in_progress", Mock(return_value=applied))
        monkeypatch.setattr(_shared, "capture_event", lambda *_a, **_k: None)
        _patch_row(monkeypatch, row)
        assert await _run(complete_transcription.complete_transcription, str(TRANSCRIPTION_ID)) is expected, (
            applied,
            expected,
        )


# --- summarise ---


@pytest.fixture
def summary_version(monkeypatch):
    version_id = uuid.uuid4()
    monkeypatch.setattr(
        MinuteHandlerService,
        "get_initial_minute_version_for_minute_id",
        AsyncMock(return_value=SimpleNamespace(id=version_id)),
    )
    return version_id


@pytest.mark.asyncio
async def test_summarise_generates_initial_version(monkeypatch, summary_version):
    generate = AsyncMock()
    monkeypatch.setattr(MinuteHandlerService, "process_minute_generation_message", generate)
    await _run(summarise.summarise, str(MINUTE_ID))
    generate.assert_awaited_once_with(summary_version)


@pytest.mark.asyncio
async def test_summarise_handled_failure_is_non_retryable(monkeypatch, summary_version):  # noqa: ARG001
    monkeypatch.setattr(
        MinuteHandlerService, "process_minute_generation_message", AsyncMock(side_effect=MinuteGenerationFailedError)
    )
    with pytest.raises(ApplicationError) as e:
        await _run(summarise.summarise, str(MINUTE_ID))
    assert e.value.non_retryable


@pytest.mark.asyncio
async def test_fail_summarise_finalises_only_initial_version(monkeypatch, summary_version):
    recorded = Mock()
    monkeypatch.setattr(MinuteHandlerService, "record_minute_version_failure", recorded)
    await _run(fail_minute.fail_summarise, wf.FailTranscriptionInput(str(MINUTE_ID), "exhausted retries"))
    recorded.assert_called_once_with(summary_version, "exhausted retries")


# --- generate_minute / edit_minute (user-created minutes and AI edits) ---


@pytest.mark.asyncio
async def test_generate_minute_generates_the_version(monkeypatch):
    generate = AsyncMock()
    monkeypatch.setattr(MinuteHandlerService, "process_minute_generation_message", generate)
    await _run(generate_minute.generate_minute, str(MINUTE_ID))
    generate.assert_awaited_once_with(MINUTE_ID)


@pytest.mark.asyncio
async def test_generate_minute_error_mapping(monkeypatch):
    for raises, non_retryable in ((MinuteGenerationFailedError(), True), (MinuteGenerationTransientError(), False)):
        monkeypatch.setattr(MinuteHandlerService, "process_minute_generation_message", AsyncMock(side_effect=raises))
        with pytest.raises(ApplicationError) as e:
            await _run(generate_minute.generate_minute, str(MINUTE_ID))
        assert e.value.non_retryable is non_retryable


@pytest.mark.asyncio
async def test_edit_minute_passes_target_and_source(monkeypatch):
    edit = AsyncMock()
    monkeypatch.setattr(MinuteHandlerService, "process_minute_edit_message", edit)
    params = minute_wf.MinuteEditInput(minute_version_id=str(TRANSCRIPTION_ID), source_minute_version_id=str(MINUTE_ID))
    await _run(edit_minute.edit_minute, params)
    edit.assert_awaited_once_with(target_minute_version_id=TRANSCRIPTION_ID, source_minute_version_id=MINUTE_ID)


@pytest.mark.asyncio
async def test_edit_minute_error_mapping(monkeypatch):
    params = minute_wf.MinuteEditInput(minute_version_id=str(TRANSCRIPTION_ID), source_minute_version_id=str(MINUTE_ID))
    for raises, non_retryable in ((MinuteGenerationFailedError, True), (MinuteGenerationTransientError, False)):
        monkeypatch.setattr(MinuteHandlerService, "process_minute_edit_message", AsyncMock(side_effect=raises))
        with pytest.raises(ApplicationError) as e:
            await _run(edit_minute.edit_minute, params)
        assert e.value.non_retryable is non_retryable

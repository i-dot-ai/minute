"""Branch tests for the transcription activities: how each maps outcomes to Temporal results.

Collaborators are patched; ActivityEnvironment runs each activity in-process (no server, no DB).
"""

import uuid
from types import SimpleNamespace

import pytest
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


def _row(status=JobStatus.IN_PROGRESS, entries=ENTRIES):
    return SimpleNamespace(id=TRANSCRIPTION_ID, user_id=uuid.uuid4(), status=status, dialogue_entries=entries)


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
    monkeypatch.setattr(_shared, "capture_event", lambda *_a, **_k: None)
    return calls


def _patch_row(monkeypatch, row):
    """Patch the row every activity reads (in_progress and complete_transcription both use it)."""
    in_progress = lambda _tid: row if row and row.status == JobStatus.IN_PROGRESS else None  # noqa: E731
    monkeypatch.setattr(_shared, "in_progress", in_progress)
    monkeypatch.setattr(_shared, "get_row", lambda _tid: row)


def _patch_load(monkeypatch, row):
    """Patch the minute -> transcription lookup (fail_transcription reads it by minute id)."""
    monkeypatch.setattr(_shared, "load", lambda _minute_id: row)


# --- prepare_audio ---


def _patch_audio_step(monkeypatch, *, result=None, raises=None):
    async def _step(_minute_id):
        if raises:
            raise raises
        return result

    monkeypatch.setattr(prepare_audio, "_prepare_audio", _step)


async def _run_prepare_audio():
    return await _run(prepare_audio.prepare_audio, str(MINUTE_ID))


@pytest.mark.asyncio
async def test_prepare_audio_reports_duration(monkeypatch):
    _patch_audio_step(monkeypatch, result=wf.PreparedAudio(duration_seconds=7200.0))
    assert await _run_prepare_audio() == wf.PreparedAudio(duration_seconds=7200.0)


@pytest.mark.asyncio
async def test_prepare_audio_bad_audio_is_non_retryable(monkeypatch):
    _patch_audio_step(monkeypatch, raises=TranscriptionFailedError("no audio stream"))
    with pytest.raises(ApplicationError) as e:
        await _run_prepare_audio()
    assert e.value.non_retryable


@pytest.mark.asyncio
async def test_prepare_audio_transient_error_is_retryable(monkeypatch):
    _patch_audio_step(monkeypatch, raises=_shared.TranscriptionTransientError("row moved on"))
    with pytest.raises(ApplicationError) as e:
        await _run_prepare_audio()
    assert not e.value.non_retryable


# --- transcribe ---


def _patch_transcribe_step(monkeypatch, *, result=None, raises=None, seen=None):
    async def _step(params):
        if seen is not None:
            seen.append(params)
        if raises:
            raise raises
        return result

    monkeypatch.setattr(transcribe, "_transcribe", _step)


async def _transcribe():
    return await ActivityEnvironment().run(transcribe.transcribe, TRANSCRIBE_INPUT)


@pytest.mark.asyncio
async def test_transcribe_returns_id(monkeypatch):
    seen: list = []
    _patch_transcribe_step(monkeypatch, result=str(TRANSCRIPTION_ID), seen=seen)
    assert await _transcribe() == str(TRANSCRIPTION_ID)
    assert seen == [TRANSCRIBE_INPUT]


@pytest.mark.asyncio
async def test_transcribe_provider_unavailable_is_retryable(monkeypatch):
    _patch_transcribe_step(monkeypatch, raises=_shared.TranscriptionTransientError("provider 429"))
    with pytest.raises(ApplicationError) as e:
        await _transcribe()
    assert not e.value.non_retryable


@pytest.mark.asyncio
async def test_transcribe_handled_failure_is_non_retryable(monkeypatch):
    _patch_transcribe_step(monkeypatch, raises=TranscriptionFailedError("azure said no"))
    with pytest.raises(ApplicationError) as e:
        await _transcribe()
    assert e.value.non_retryable


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
    def _gone(_minute_id):
        raise TranscriptionFailedError

    monkeypatch.setattr(_shared, "load", _gone)
    params = wf.FailTranscriptionInput(minute_id=str(MINUTE_ID), error="x")
    await _run(fail_transcription.fail_transcription, params)
    assert writes == []


# --- identify_speakers / generate_title ---


@pytest.mark.asyncio
async def test_identify_speakers_saves_named_entries(monkeypatch, writes):
    named = [{**ENTRIES[0], "speaker": "Alice"}]

    async def _name(_entries):
        return named

    _patch_row(monkeypatch, _row())
    monkeypatch.setattr(TranscriptionHandlerService, "identify_speakers", _name)
    await _run(identify_speakers.identify_speakers, str(TRANSCRIPTION_ID))
    assert writes == [(TRANSCRIPTION_ID, {"dialogue_entries": named})]


@pytest.mark.asyncio
@pytest.mark.parametrize("status", [JobStatus.IN_PROGRESS, JobStatus.COMPLETED])
async def test_generate_title_saves_title(monkeypatch, writes, status):
    async def _title(transcript):
        assert transcript == ENTRIES
        return "Weekly sync"

    _patch_row(monkeypatch, _row(status))
    monkeypatch.setattr(generate_title, "generate_meeting_title", _title)
    await _run(generate_title.generate_title, str(TRANSCRIPTION_ID))
    assert writes == [(TRANSCRIPTION_ID, {"title": "Weekly sync"})]


@pytest.mark.asyncio
@pytest.mark.parametrize("fn", [identify_speakers.identify_speakers, generate_title.generate_title])
@pytest.mark.parametrize("row", [None, _row(JobStatus.FAILED)])
async def test_post_processing_skips_rows_no_longer_in_progress(monkeypatch, writes, fn, row):
    _patch_row(monkeypatch, row)
    await _run(fn, str(TRANSCRIPTION_ID))
    assert writes == []


@pytest.mark.asyncio
async def test_title_llm_error_propagates_for_temporal_to_retry(monkeypatch, writes):
    async def _boom(*, transcript):  # noqa: ARG001
        msg = "llm down"
        raise RuntimeError(msg)

    _patch_row(monkeypatch, _row())
    monkeypatch.setattr(generate_title, "generate_meeting_title", _boom)
    with pytest.raises(RuntimeError):
        await _run(generate_title.generate_title, str(TRANSCRIPTION_ID))
    assert writes == []


# --- complete_transcription ---


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("applied", "row", "expected"),
    [
        (True, _row(), True),
        (False, _row(JobStatus.COMPLETED), True),  # retry after an earlier attempt already completed it
        (False, _row(JobStatus.FAILED), False),
        (False, None, False),  # deleted
    ],
)
async def test_complete_transcription(monkeypatch, applied, row, expected):
    monkeypatch.setattr(_shared, "update_in_progress", lambda _tid, **_v: applied)
    monkeypatch.setattr(_shared, "capture_event", lambda *_a, **_k: None)
    _patch_row(monkeypatch, row)
    assert await _run(complete_transcription.complete_transcription, str(TRANSCRIPTION_ID)) is expected


# --- summarise ---


def _patch_summarise(monkeypatch, *, raises=None):
    version_id = uuid.uuid4()
    seen: list = []

    async def _only(_mid):
        return SimpleNamespace(id=version_id)

    async def _generate(mvid):
        seen.append(mvid)
        if raises:
            raise raises

    monkeypatch.setattr(summarise.MinuteHandlerService, "get_initial_minute_version_for_minute_id", _only)
    monkeypatch.setattr(summarise.MinuteHandlerService, "process_minute_generation_message", _generate)
    return version_id, seen


@pytest.mark.asyncio
async def test_summarise_generates_initial_version(monkeypatch):
    version_id, seen = _patch_summarise(monkeypatch)
    await _run(summarise.summarise, str(MINUTE_ID))
    assert seen == [version_id]


@pytest.mark.asyncio
async def test_summarise_handled_failure_is_non_retryable(monkeypatch):
    _patch_summarise(monkeypatch, raises=MinuteGenerationFailedError())
    with pytest.raises(ApplicationError) as e:
        await _run(summarise.summarise, str(MINUTE_ID))
    assert e.value.non_retryable


# --- generate_minute / edit_minute (user-created minutes and AI edits) ---


@pytest.mark.asyncio
async def test_generate_minute_generates_the_version(monkeypatch):
    seen: list = []

    async def _generate(mvid):
        seen.append(mvid)

    monkeypatch.setattr(MinuteHandlerService, "process_minute_generation_message", _generate)
    await _run(generate_minute.generate_minute, str(MINUTE_ID))
    assert seen == [MINUTE_ID]


@pytest.mark.asyncio
async def test_generate_minute_handled_failure_is_non_retryable(monkeypatch):
    _patch_summarise(monkeypatch, raises=MinuteGenerationFailedError())
    with pytest.raises(ApplicationError) as e:
        await _run(generate_minute.generate_minute, str(MINUTE_ID))
    assert e.value.non_retryable


@pytest.mark.asyncio
async def test_generate_minute_transient_error_is_retryable(monkeypatch):
    _patch_summarise(monkeypatch, raises=MinuteGenerationTransientError())
    with pytest.raises(ApplicationError) as e:
        await _run(generate_minute.generate_minute, str(MINUTE_ID))
    assert not e.value.non_retryable


@pytest.mark.asyncio
async def test_edit_minute_passes_target_and_source(monkeypatch):
    seen: list = []

    async def _edit(target_minute_version_id, source_minute_version_id):
        seen.append((target_minute_version_id, source_minute_version_id))

    monkeypatch.setattr(MinuteHandlerService, "process_minute_edit_message", _edit)
    params = minute_wf.MinuteEditInput(minute_version_id=str(TRANSCRIPTION_ID), source_minute_version_id=str(MINUTE_ID))
    await _run(edit_minute.edit_minute, params)
    assert seen == [(TRANSCRIPTION_ID, MINUTE_ID)]


@pytest.mark.asyncio
async def test_edit_minute_handled_failure_is_non_retryable(monkeypatch):
    async def _edit(**_kwargs):
        raise MinuteGenerationFailedError

    monkeypatch.setattr(MinuteHandlerService, "process_minute_edit_message", _edit)
    params = minute_wf.MinuteEditInput(minute_version_id=str(TRANSCRIPTION_ID), source_minute_version_id=str(MINUTE_ID))
    with pytest.raises(ApplicationError) as e:
        await _run(edit_minute.edit_minute, params)
    assert e.value.non_retryable


@pytest.mark.asyncio
async def test_edit_minute_transient_error_is_retryable(monkeypatch):
    async def _edit(**_kwargs):
        raise MinuteGenerationTransientError

    monkeypatch.setattr(MinuteHandlerService, "process_minute_edit_message", _edit)
    params = minute_wf.MinuteEditInput(minute_version_id=str(TRANSCRIPTION_ID), source_minute_version_id=str(MINUTE_ID))
    with pytest.raises(ApplicationError) as e:
        await _run(edit_minute.edit_minute, params)
    assert not e.value.non_retryable

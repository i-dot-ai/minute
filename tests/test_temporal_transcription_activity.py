"""Branch tests for the transcription activities: how each maps outcomes to Temporal results.

Collaborators are patched; ActivityEnvironment runs each activity in-process (no server, no DB).
"""

import uuid
from types import SimpleNamespace
from typing import cast

import pytest
from temporalio.exceptions import ApplicationError
from temporalio.testing import ActivityEnvironment

from common.runtime import Runtime
from common.services.minute_handler_service import MinuteDelivery, MinuteGenerationFailedError
from common.services.stt import TranscriptionFailedError, TranscriptionTransientError
from common.types import DialogueEntry, JobStatus
from common.workflows import transcription as wf
from common.workflows.activities import (
    _shared,
    complete_transcription,
    fail_transcription,
    generate_title,
    identify_speakers,
    prepare_audio,
    summarize,
    transcribe,
)

MINUTE_ID = uuid.uuid4()
TRANSCRIPTION_ID = uuid.uuid4()
ENTRIES: list[DialogueEntry] = [DialogueEntry(speaker="A", text="hi", start_time=0.0, end_time=1.0)]
TRANSCRIBE_INPUT = wf.TranscribeInput(minute_id=str(MINUTE_ID), stt_timeout_seconds=60)
# The step functions are patched in these tests, so the runtime's providers are never read.
RUNTIME = cast(Runtime, SimpleNamespace(storage=None, stt=None, db=None))


def _row(status=JobStatus.IN_PROGRESS, entries=ENTRIES):
    return SimpleNamespace(id=TRANSCRIPTION_ID, user_id=uuid.uuid4(), status=status, dialogue_entries=entries)


async def _run(fn, arg):
    return await ActivityEnvironment().run(fn, arg)


@pytest.fixture
def writes(monkeypatch):
    """Record IN_PROGRESS-guarded writes; returns True (row was IN_PROGRESS)."""
    calls: list = []

    async def _update(tid, **values):
        calls.append((tid, values))
        return True

    monkeypatch.setattr(_shared, "update_in_progress", _update)
    monkeypatch.setattr(_shared, "capture_event", lambda *_a, **_k: None)
    return calls


def _patch_row(monkeypatch, row):
    """Patch the row every activity reads (in_progress and complete_transcription both use it)."""

    async def _get(_tid):
        return row

    monkeypatch.setattr(_shared, "get_row", _get)


def _patch_load(monkeypatch, row):
    """Patch the minute -> transcription lookup (fail_transcription reads it by minute id)."""

    async def _load(_minute_id):
        return row

    monkeypatch.setattr(_shared, "load", _load)


# --- prepare_audio ---


def _patch_audio_step(monkeypatch, *, result=None, raises=None):
    async def _step(_minute_id, _runtime):
        if raises:
            raise raises
        return result

    monkeypatch.setattr(prepare_audio, "_prepare_audio", _step)


async def _run_prepare_audio():
    return await _run(prepare_audio.build_prepare_audio(RUNTIME), str(MINUTE_ID))


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
    _patch_audio_step(monkeypatch, raises=TranscriptionTransientError("claim moved"))
    with pytest.raises(ApplicationError) as e:
        await _run_prepare_audio()
    assert not e.value.non_retryable


# --- transcribe ---


def _patch_transcribe_step(monkeypatch, *, result=None, raises=None, seen=None):
    async def _step(params, attempt, runtime):  # noqa: ARG001
        if seen is not None:
            seen.append((params, attempt))
        if raises:
            raise raises
        return result

    monkeypatch.setattr(transcribe, "_transcribe", _step)


async def _transcribe():
    return await ActivityEnvironment().run(transcribe.build_transcribe(RUNTIME), TRANSCRIBE_INPUT)


@pytest.mark.asyncio
async def test_transcribe_returns_id_and_passes_the_attempt(monkeypatch):
    seen: list = []
    _patch_transcribe_step(monkeypatch, result=str(TRANSCRIPTION_ID), seen=seen)
    assert await _transcribe() == str(TRANSCRIPTION_ID)
    # ActivityEnvironment runs attempt 1; the region is chosen from it by the STT provider.
    assert seen == [(TRANSCRIBE_INPUT, 1)]


@pytest.mark.asyncio
async def test_transcribe_provider_unavailable_is_retryable(monkeypatch):
    _patch_transcribe_step(monkeypatch, raises=TranscriptionTransientError("every region 429"))
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
    async def _gone(_minute_id):
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
    monkeypatch.setattr(identify_speakers, "process_speakers_and_dialogue_entries", _name)
    await _run(identify_speakers.identify_speakers, str(TRANSCRIPTION_ID))
    assert writes == [(TRANSCRIPTION_ID, {"dialogue_entries": named})]


@pytest.mark.asyncio
async def test_generate_title_saves_title(monkeypatch, writes):
    async def _title(transcript):
        assert transcript == ENTRIES
        return "Weekly sync"

    _patch_row(monkeypatch, _row())
    monkeypatch.setattr(generate_title, "generate_meeting_title", _title)
    await _run(generate_title.generate_title, str(TRANSCRIPTION_ID))
    assert writes == [(TRANSCRIPTION_ID, {"title": "Weekly sync"})]


@pytest.mark.asyncio
async def test_generate_title_llm_error_propagates_for_retry(monkeypatch, writes):
    async def _boom(transcript):  # noqa: ARG001
        msg = "llm down"
        raise RuntimeError(msg)

    _patch_row(monkeypatch, _row())
    monkeypatch.setattr(generate_title, "generate_meeting_title", _boom)
    with pytest.raises(RuntimeError):
        await _run(generate_title.generate_title, str(TRANSCRIPTION_ID))
    assert writes == []


@pytest.mark.asyncio
@pytest.mark.parametrize("fn", [identify_speakers.identify_speakers, generate_title.generate_title])
@pytest.mark.parametrize("row", [None, _row(JobStatus.FAILED)])
async def test_post_processing_skips_rows_no_longer_in_progress(monkeypatch, writes, fn, row):
    _patch_row(monkeypatch, row)
    await _run(fn, str(TRANSCRIPTION_ID))
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
    async def _update(_tid, **_v):
        return applied

    monkeypatch.setattr(_shared, "update_in_progress", _update)
    monkeypatch.setattr(_shared, "capture_event", lambda *_a, **_k: None)
    _patch_row(monkeypatch, row)
    assert await _run(complete_transcription.complete_transcription, str(TRANSCRIPTION_ID)) is expected


# --- summarize ---


def _patch_summarize(monkeypatch, *, delivery=MinuteDelivery.ACK, raises=None):
    version_id = uuid.uuid4()
    seen: list = []

    async def _only(_mid):
        return SimpleNamespace(id=version_id)

    async def _generate(mvid):
        seen.append(mvid)
        if raises:
            raise raises
        return delivery

    monkeypatch.setattr(summarize.MinuteHandlerService, "get_only_minute_version_for_minute_id", _only)
    monkeypatch.setattr(summarize.MinuteHandlerService, "process_minute_generation_message", _generate)
    return version_id, seen


@pytest.mark.asyncio
async def test_summarize_generates_initial_version(monkeypatch):
    version_id, seen = _patch_summarize(monkeypatch)
    await _run(summarize.summarize, str(MINUTE_ID))
    assert seen == [version_id]


@pytest.mark.asyncio
async def test_summarize_handled_failure_is_non_retryable(monkeypatch):
    _patch_summarize(monkeypatch, raises=MinuteGenerationFailedError())
    with pytest.raises(ApplicationError) as e:
        await _run(summarize.summarize, str(MINUTE_ID))
    assert e.value.non_retryable


@pytest.mark.asyncio
async def test_summarize_claimed_elsewhere_retries(monkeypatch):
    _patch_summarize(monkeypatch, delivery=MinuteDelivery.LEAVE)
    with pytest.raises(ApplicationError) as e:
        await _run(summarize.summarize, str(MINUTE_ID))
    assert not e.value.non_retryable

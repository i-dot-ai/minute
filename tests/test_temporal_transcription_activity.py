"""Branch tests for the Temporal transcription activities.

DB and LLM calls are patched; this checks how each activity maps outcomes to
Temporal results. ActivityEnvironment runs activities in-process (no server, no DB).
"""

import uuid
from types import SimpleNamespace

import pytest
from temporalio.exceptions import ApplicationError
from temporalio.testing import ActivityEnvironment

from common.database.postgres_models import JobStatus
from common.services.exceptions import TranscriptionFailedError
from common.services.minute_handler_service import MinuteDelivery, MinuteGenerationFailedError
from common.types import DialogueEntry, TranscriptionJobMessageData
from worker import temporal_activities as acts

MINUTE_ID = uuid.uuid4()
TRANSCRIPTION_ID = uuid.uuid4()
ENTRIES: list[DialogueEntry] = [DialogueEntry(speaker="A", text="hi", start_time=0.0, end_time=1.0)]
DONE = TranscriptionJobMessageData(transcription_service="azure_stt_synchronous", transcript=ENTRIES)
Handler = acts.TranscriptionHandlerService


def _row(status=JobStatus.IN_PROGRESS, entries=ENTRIES):
    return SimpleNamespace(id=TRANSCRIPTION_ID, user_id=uuid.uuid4(), status=status, dialogue_entries=entries)


async def _run(fn, arg):
    return await ActivityEnvironment().run(fn, str(arg))


@pytest.fixture
def writes(monkeypatch):
    """Record update_in_progress_transcription calls; returns True (row was IN_PROGRESS)."""
    calls: list = []

    def _update(tid, **values):
        calls.append((tid, values))
        return True

    monkeypatch.setattr(Handler, "update_in_progress_transcription", _update)
    monkeypatch.setattr(acts, "capture_event", lambda *_a, **_k: None)
    return calls


def _patch_transcribe(monkeypatch, *, result=None, raises=None, row=None):
    async def _process(minute_id, *, post_process):  # noqa: ARG001
        assert post_process is False
        if raises:
            raise raises
        return result

    monkeypatch.setattr(Handler, "process_transcription", _process)
    monkeypatch.setattr(Handler, "get_transcription_from_minute_id", lambda _mid: row or _row())


# --- transcribe ---


@pytest.mark.asyncio
async def test_transcribe_returns_transcription_id(monkeypatch):
    _patch_transcribe(monkeypatch, result=DONE)
    assert await _run(acts.transcribe, MINUTE_ID) == str(TRANSCRIPTION_ID)


@pytest.mark.asyncio
async def test_transcribe_handled_failure_is_non_retryable(monkeypatch):
    _patch_transcribe(monkeypatch, raises=TranscriptionFailedError("azure said no"))
    with pytest.raises(ApplicationError) as e:
        await _run(acts.transcribe, MINUTE_ID)
    assert e.value.non_retryable


@pytest.mark.asyncio
async def test_transcribe_unhandled_error_is_retryable(monkeypatch):
    _patch_transcribe(monkeypatch, raises=RuntimeError("db blip"))
    with pytest.raises(RuntimeError):
        await _run(acts.transcribe, MINUTE_ID)


@pytest.mark.asyncio
async def test_transcribe_async_provider_rejected(monkeypatch):
    _patch_transcribe(monkeypatch, result=TranscriptionJobMessageData(transcription_service="aws", job_name="j"))
    with pytest.raises(ApplicationError) as e:
        await _run(acts.transcribe, MINUTE_ID)
    assert e.value.non_retryable


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("row", "expect"),
    [
        (_row(JobStatus.IN_PROGRESS, ENTRIES), "ok"),  # earlier attempt saved the transcript, then died
        (_row(JobStatus.COMPLETED), "ok"),
        (_row(JobStatus.IN_PROGRESS, None), "retry"),  # earlier attempt still owns the claim
        (_row(JobStatus.FAILED), "fatal"),
    ],
)
async def test_transcribe_lost_claim(monkeypatch, row, expect):
    _patch_transcribe(monkeypatch, result=None, row=row)
    if expect == "ok":
        assert await _run(acts.transcribe, MINUTE_ID) == str(TRANSCRIPTION_ID)
        return
    with pytest.raises(ApplicationError) as e:
        await _run(acts.transcribe, MINUTE_ID)
    assert e.value.non_retryable == (expect == "fatal")


# --- identify_speakers / generate_title ---


@pytest.mark.asyncio
async def test_identify_speakers_saves_named_entries(monkeypatch, writes):
    named = [{**ENTRIES[0], "speaker": "Alice"}]

    async def _name(_entries):
        return named

    monkeypatch.setattr(Handler, "get_transcription_row", lambda _tid: _row())
    monkeypatch.setattr(acts, "process_speakers_and_dialogue_entries", _name)
    await _run(acts.identify_speakers, TRANSCRIPTION_ID)
    assert writes == [(TRANSCRIPTION_ID, {"dialogue_entries": named})]


@pytest.mark.asyncio
async def test_generate_title_saves_title(monkeypatch, writes):
    async def _title(transcript):
        assert transcript == ENTRIES
        return "Weekly sync"

    monkeypatch.setattr(Handler, "get_transcription_row", lambda _tid: _row())
    monkeypatch.setattr(acts, "generate_meeting_title", _title)
    await _run(acts.generate_title, TRANSCRIPTION_ID)
    assert writes == [(TRANSCRIPTION_ID, {"title": "Weekly sync"})]


@pytest.mark.asyncio
async def test_generate_title_llm_error_propagates_for_retry(monkeypatch, writes):
    async def _boom(transcript):  # noqa: ARG001
        msg = "llm down"
        raise RuntimeError(msg)

    monkeypatch.setattr(Handler, "get_transcription_row", lambda _tid: _row())
    monkeypatch.setattr(acts, "generate_meeting_title", _boom)
    with pytest.raises(RuntimeError):
        await _run(acts.generate_title, TRANSCRIPTION_ID)
    assert writes == []


@pytest.mark.asyncio
@pytest.mark.parametrize("fn", [acts.identify_speakers, acts.generate_title])
@pytest.mark.parametrize("row", [None, _row(JobStatus.FAILED)])
async def test_post_processing_skips_rows_no_longer_in_progress(monkeypatch, writes, fn, row):
    monkeypatch.setattr(Handler, "get_transcription_row", lambda _tid: row)
    await _run(fn, TRANSCRIPTION_ID)
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
    monkeypatch.setattr(Handler, "update_in_progress_transcription", lambda _tid, **_v: applied)
    monkeypatch.setattr(Handler, "get_transcription_row", lambda _tid: row)
    monkeypatch.setattr(acts, "capture_event", lambda *_a, **_k: None)
    assert await _run(acts.complete_transcription, TRANSCRIPTION_ID) is expected


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

    monkeypatch.setattr(acts.MinuteHandlerService, "get_only_minute_version_for_minute_id", _only)
    monkeypatch.setattr(acts.MinuteHandlerService, "process_minute_generation_message", _generate)
    return version_id, seen


@pytest.mark.asyncio
async def test_summarize_generates_initial_version(monkeypatch):
    version_id, seen = _patch_summarize(monkeypatch)
    await _run(acts.summarize, MINUTE_ID)
    assert seen == [version_id]


@pytest.mark.asyncio
async def test_summarize_handled_failure_is_non_retryable(monkeypatch):
    _patch_summarize(monkeypatch, raises=MinuteGenerationFailedError())
    with pytest.raises(ApplicationError) as e:
        await _run(acts.summarize, MINUTE_ID)
    assert e.value.non_retryable


@pytest.mark.asyncio
async def test_summarize_claimed_elsewhere_retries(monkeypatch):
    _patch_summarize(monkeypatch, delivery=MinuteDelivery.LEAVE)
    with pytest.raises(ApplicationError) as e:
        await _run(acts.summarize, MINUTE_ID)
    assert not e.value.non_retryable

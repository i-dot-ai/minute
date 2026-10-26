"""Workflow-level test: step order, routing, timeouts and graceful degradation, with every activity mocked.

Uses Temporal's time-skipping test server (downloaded and cached by the SDK on first
run), so retry backoffs complete instantly. No DB, LLM or STT is touched.
"""

import asyncio
import uuid
from datetime import timedelta

import pytest
from temporalio import activity
from temporalio.client import WorkflowFailureError
from temporalio.exceptions import ApplicationError
from temporalio.testing import WorkflowEnvironment
from temporalio.worker import Worker

from common.workflows import transcription as wf

MINUTE_ID = str(uuid.uuid4())
TRANSCRIPTION_ID = str(uuid.uuid4())
AUDIO_SECONDS = 7200.0  # 2h


def _activities(calls: list, *, fail: frozenset = frozenset(), completed: bool = True, seen: dict | None = None):
    """Mock every activity by name; names in `fail` raise a non-retryable error. `seen` records inputs/timeouts."""
    seen = {} if seen is None else seen

    def _maybe_fail(name):
        calls.append((name, activity.info().task_queue))
        if name in fail:
            msg = f"{name} broke"
            raise ApplicationError(msg, non_retryable=True)

    @activity.defn(name=wf.PREPARE_AUDIO)
    async def prepare_audio(_minute_id: str) -> wf.PreparedAudio:
        _maybe_fail(wf.PREPARE_AUDIO)
        return wf.PreparedAudio(duration_seconds=AUDIO_SECONDS)

    @activity.defn(name=wf.TRANSCRIBE)
    async def transcribe(params: wf.TranscribeInput) -> str:
        seen["transcribe_input"] = params
        seen["transcribe_timeout"] = activity.info().start_to_close_timeout
        seen["transcribe_heartbeat_timeout"] = activity.info().heartbeat_timeout
        _maybe_fail(wf.TRANSCRIBE)
        return TRANSCRIPTION_ID

    @activity.defn(name=wf.FAIL_TRANSCRIPTION)
    async def fail_transcription(params: wf.FailTranscriptionInput) -> None:
        seen["fail_input"] = params
        _maybe_fail(wf.FAIL_TRANSCRIPTION)

    @activity.defn(name=wf.IDENTIFY_SPEAKERS)
    async def identify_speakers(_tid: str) -> None:
        _maybe_fail(wf.IDENTIFY_SPEAKERS)

    @activity.defn(name=wf.GENERATE_TITLE)
    async def generate_title(_tid: str) -> None:
        _maybe_fail(wf.GENERATE_TITLE)

    @activity.defn(name=wf.COMPLETE_TRANSCRIPTION)
    async def complete_transcription(_tid: str) -> bool:
        _maybe_fail(wf.COMPLETE_TRANSCRIPTION)
        return completed

    @activity.defn(name=wf.SUMMARISE)
    async def summarise(_minute_id: str) -> None:
        _maybe_fail(wf.SUMMARISE)

    # Same grouping as common/workflows/activities/__init__.py: {task queue: activities}
    return {
        wf.STT_TASK_QUEUE: [prepare_audio, transcribe],
        wf.LLM_TASK_QUEUE: [identify_speakers, generate_title, summarise],
        wf.TASK_QUEUE: [complete_transcription, fail_transcription],
    }


def _workers(client, by_queue: dict, **caps) -> list[Worker]:
    """One Worker per queue, mirroring worker/temporal_worker.py."""
    return [
        Worker(
            client,
            task_queue=queue,
            activities=acts,
            workflows=[wf.TranscriptionWorkflow] if queue == wf.TASK_QUEUE else [],
            **({"max_concurrent_activities": caps[queue]} if queue in caps else {}),
        )
        for queue, acts in by_queue.items()
    ]


async def _run(**kwargs) -> tuple[list, dict, dict]:
    calls: list = []
    async with await WorkflowEnvironment.start_time_skipping() as env:
        workers = _workers(env.client, _activities(calls, **kwargs))
        async with workers[0], workers[1], workers[2]:
            outcome = await env.client.execute_workflow(
                wf.TranscriptionWorkflow.run, MINUTE_ID, id=wf.workflow_id(TRANSCRIPTION_ID), task_queue=wf.TASK_QUEUE
            )
    return [name for name, _ in calls], outcome, dict(calls)


SEQUENTIAL_STEPS = [wf.PREPARE_AUDIO, wf.TRANSCRIBE, wf.IDENTIFY_SPEAKERS, wf.COMPLETE_TRANSCRIPTION]
PARALLEL_STEPS = [wf.GENERATE_TITLE, wf.SUMMARISE]


def _assert_all_steps_ran(calls: list) -> None:
    """Title and summary run concurrently after completion, so their relative order is not fixed."""
    assert calls[:4] == SEQUENTIAL_STEPS
    assert sorted(calls[4:]) == sorted(PARALLEL_STEPS)


@pytest.mark.asyncio
async def test_happy_path_runs_every_step_in_order_on_its_queue():
    calls, outcome, queue_of = await _run()
    _assert_all_steps_ran(calls)
    assert queue_of == {
        wf.PREPARE_AUDIO: wf.STT_TASK_QUEUE,
        wf.TRANSCRIBE: wf.STT_TASK_QUEUE,
        wf.IDENTIFY_SPEAKERS: wf.LLM_TASK_QUEUE,
        wf.GENERATE_TITLE: wf.LLM_TASK_QUEUE,
        wf.SUMMARISE: wf.LLM_TASK_QUEUE,
        wf.COMPLETE_TRANSCRIPTION: wf.TASK_QUEUE,
    }
    assert outcome == {wf.IDENTIFY_SPEAKERS: "ok", wf.GENERATE_TITLE: "ok", wf.SUMMARISE: "ok"}


def test_stt_timeout_scales_with_audio_duration():
    for duration, expected in (
        (0, timedelta(minutes=5)),
        (98, timedelta(minutes=5, seconds=9.8)),
        (7200, timedelta(minutes=17)),
    ):
        assert wf.stt_timeout(duration) == expected


@pytest.mark.asyncio
async def test_transcribe_gets_duration_based_timeout():
    seen: dict = {}
    await _run(seen=seen)
    expected = wf.stt_timeout(AUDIO_SECONDS)
    assert seen["transcribe_timeout"] == expected
    assert seen["transcribe_heartbeat_timeout"] == timedelta(seconds=90)
    params = seen["transcribe_input"]
    assert params.minute_id == MINUTE_ID
    # Azure's budget leaves room inside the activity timeout for the mp3 download
    assert params.stt_timeout_seconds == (expected - wf.STT_DOWNLOAD_MARGIN).total_seconds()


@pytest.mark.asyncio
async def test_optional_step_failure_degrades():
    for broken in (wf.IDENTIFY_SPEAKERS, wf.GENERATE_TITLE, wf.SUMMARISE):
        calls, outcome, _ = await _run(fail=frozenset({broken}))
        _assert_all_steps_ran(calls)  # everything still runs
        assert outcome[broken].startswith("failed:"), broken
        assert all(v == "ok" for k, v in outcome.items() if k != broken), broken


@pytest.mark.asyncio
async def test_transcription_no_longer_in_progress_skips_summary_and_title():
    calls, outcome, _ = await _run(completed=False)
    assert wf.SUMMARISE not in calls
    assert wf.GENERATE_TITLE not in calls
    assert outcome[wf.SUMMARISE].startswith("skipped")
    assert outcome[wf.GENERATE_TITLE].startswith("skipped")


@pytest.mark.asyncio
async def test_audio_or_stt_failure_marks_failed_and_fails_the_run():
    for broken in (wf.PREPARE_AUDIO, wf.TRANSCRIBE):
        calls: list = []
        seen: dict = {}
        async with await WorkflowEnvironment.start_time_skipping() as env:
            workers = _workers(env.client, _activities(calls, fail=frozenset({broken}), seen=seen))
            async with workers[0], workers[1], workers[2]:
                with pytest.raises(WorkflowFailureError):
                    await env.client.execute_workflow(
                        wf.TranscriptionWorkflow.run, MINUTE_ID, id=str(uuid.uuid4()), task_queue=wf.TASK_QUEUE
                    )
        assert [name for name, _ in calls][-1] == wf.FAIL_TRANSCRIPTION, broken  # row isn't left IN_PROGRESS
        assert f"{broken} broke" in seen["fail_input"].error
        assert wf.IDENTIFY_SPEAKERS not in [name for name, _ in calls], broken


@pytest.mark.asyncio
async def test_completion_failure_marks_failed_and_fails_the_run():
    """A post-transcribe failure (e.g. a DB blip on the completion write) closes the row too, so it
    isn't left IN_PROGRESS for the cleanup sweeper."""
    calls: list = []
    seen: dict = {}
    async with await WorkflowEnvironment.start_time_skipping() as env:
        workers = _workers(env.client, _activities(calls, fail=frozenset({wf.COMPLETE_TRANSCRIPTION}), seen=seen))
        async with workers[0], workers[1], workers[2]:
            with pytest.raises(WorkflowFailureError):
                await env.client.execute_workflow(
                    wf.TranscriptionWorkflow.run, MINUTE_ID, id=str(uuid.uuid4()), task_queue=wf.TASK_QUEUE
                )
    names = [name for name, _ in calls]
    assert names[-1] == wf.FAIL_TRANSCRIPTION
    assert wf.IDENTIFY_SPEAKERS in names  # ran before completion
    assert wf.GENERATE_TITLE not in names  # title/summary never reached
    assert wf.SUMMARISE not in names
    assert f"{wf.COMPLETE_TRANSCRIPTION} broke" in seen["fail_input"].error


@pytest.mark.asyncio
async def test_stt_worker_caps_concurrent_transcribe_calls():
    """10 uploads at once, STT worker with 4 slots: never more than 4 STT-queue activities in flight."""
    cap, runs = 4, 10
    in_flight, peak, done = 0, 0, 0

    @activity.defn(name=wf.TRANSCRIBE)
    async def transcribe(_params: wf.TranscribeInput) -> str:
        nonlocal in_flight, peak, done
        in_flight += 1
        peak = max(peak, in_flight)
        await asyncio.sleep(0.2)  # stands in for the Azure call
        in_flight -= 1
        done += 1
        return TRANSCRIPTION_ID

    by_queue = _activities([])
    by_queue[wf.STT_TASK_QUEUE] = [by_queue[wf.STT_TASK_QUEUE][0], transcribe]
    async with await WorkflowEnvironment.start_local() as env:
        workers = _workers(env.client, by_queue, **{wf.STT_TASK_QUEUE: cap})
        async with workers[0], workers[1], workers[2]:
            handles = [
                await env.client.start_workflow(
                    wf.TranscriptionWorkflow.run, str(uuid.uuid4()), id=f"cap-{i}", task_queue=wf.TASK_QUEUE
                )
                for i in range(runs)
            ]
            await asyncio.gather(*(h.result() for h in handles))

    assert done == runs
    assert peak == cap

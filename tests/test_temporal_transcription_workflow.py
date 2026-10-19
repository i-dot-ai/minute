"""Workflow-level test: step order and graceful degradation, with every activity mocked.

Uses Temporal's time-skipping test server (downloaded and cached by the SDK on first
run), so retry backoffs complete instantly. No DB, LLM or STT is touched.
"""

import asyncio
import uuid

import pytest
from temporalio import activity
from temporalio.client import WorkflowFailureError
from temporalio.exceptions import ApplicationError
from temporalio.testing import WorkflowEnvironment
from temporalio.worker import Worker

from common.workflows import transcription as wf

MINUTE_ID = str(uuid.uuid4())
TRANSCRIPTION_ID = str(uuid.uuid4())


def _activities(calls: list, *, fail: frozenset = frozenset(), completed: bool = True):
    """Mock every activity by name; names in `fail` raise a non-retryable error."""

    def _maybe_fail(name):
        calls.append((name, activity.info().task_queue))
        if name in fail:
            msg = f"{name} broke"
            raise ApplicationError(msg, non_retryable=True)

    @activity.defn(name=wf.TRANSCRIBE)
    async def transcribe(_minute_id: str) -> str:
        _maybe_fail(wf.TRANSCRIBE)
        return TRANSCRIPTION_ID

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

    @activity.defn(name=wf.SUMMARIZE)
    async def summarize(_minute_id: str) -> None:
        _maybe_fail(wf.SUMMARIZE)

    # Same grouping as worker/temporal_activities.py: {task queue: activities}
    return {
        wf.STT_TASK_QUEUE: [transcribe],
        wf.LLM_TASK_QUEUE: [identify_speakers, generate_title, summarize],
        wf.TASK_QUEUE: [complete_transcription],
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


async def _run(**kwargs) -> tuple[list, dict]:
    calls: list = []
    async with await WorkflowEnvironment.start_time_skipping() as env:
        workers = _workers(env.client, _activities(calls, **kwargs))
        async with workers[0], workers[1], workers[2]:
            outcome = await env.client.execute_workflow(
                wf.TranscriptionWorkflow.run, MINUTE_ID, id=wf.workflow_id(TRANSCRIPTION_ID), task_queue=wf.TASK_QUEUE
            )
    return [name for name, _ in calls], outcome, dict(calls)


ALL_STEPS = [wf.TRANSCRIBE, wf.IDENTIFY_SPEAKERS, wf.GENERATE_TITLE, wf.COMPLETE_TRANSCRIPTION, wf.SUMMARIZE]


@pytest.mark.asyncio
async def test_happy_path_runs_every_step_in_order_on_its_queue():
    calls, outcome, queue_of = await _run()
    assert calls == ALL_STEPS
    assert queue_of == {
        wf.TRANSCRIBE: wf.STT_TASK_QUEUE,
        wf.IDENTIFY_SPEAKERS: wf.LLM_TASK_QUEUE,
        wf.GENERATE_TITLE: wf.LLM_TASK_QUEUE,
        wf.SUMMARIZE: wf.LLM_TASK_QUEUE,
        wf.COMPLETE_TRANSCRIPTION: wf.TASK_QUEUE,
    }
    assert outcome == {wf.IDENTIFY_SPEAKERS: "ok", wf.GENERATE_TITLE: "ok", wf.SUMMARIZE: "ok"}


@pytest.mark.asyncio
@pytest.mark.parametrize("broken", [wf.IDENTIFY_SPEAKERS, wf.GENERATE_TITLE, wf.SUMMARIZE])
async def test_optional_step_failure_degrades(broken):
    calls, outcome, _ = await _run(fail=frozenset({broken}))
    assert calls == ALL_STEPS  # everything still runs
    assert outcome[broken].startswith("failed:")
    assert all(v == "ok" for k, v in outcome.items() if k != broken)


@pytest.mark.asyncio
async def test_transcription_no_longer_in_progress_skips_summary():
    calls, outcome, _ = await _run(completed=False)
    assert wf.SUMMARIZE not in calls
    assert outcome[wf.SUMMARIZE].startswith("skipped")


@pytest.mark.asyncio
async def test_transcribe_failure_fails_the_run():
    with pytest.raises(WorkflowFailureError):
        await _run(fail=frozenset({wf.TRANSCRIBE}))


@pytest.mark.asyncio
async def test_stt_worker_caps_concurrent_transcribe_calls():
    """10 uploads at once, STT worker with 4 slots: never more than 4 transcribe calls in flight."""
    cap, runs = 4, 10
    in_flight, peak, done = 0, 0, 0

    @activity.defn(name=wf.TRANSCRIBE)
    async def transcribe(_minute_id: str) -> str:
        nonlocal in_flight, peak, done
        in_flight += 1
        peak = max(peak, in_flight)
        await asyncio.sleep(0.2)  # stands in for the Azure call
        in_flight -= 1
        done += 1
        return TRANSCRIPTION_ID

    by_queue = {**_activities([]), wf.STT_TASK_QUEUE: [transcribe]}
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

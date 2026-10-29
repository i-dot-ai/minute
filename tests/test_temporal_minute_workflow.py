"""Real minute handlers must finalise DB rows after exhausted Temporal retries and timeouts."""

import asyncio
import uuid
from datetime import timedelta
from unittest.mock import AsyncMock

import httpx
import pytest
from sqlmodel.ext.asyncio.session import AsyncSession
from temporalio.client import WorkflowFailureError
from temporalio.common import RetryPolicy
from temporalio.testing import WorkflowEnvironment
from temporalio.worker import UnsandboxedWorkflowRunner, Worker

from common.database.postgres_database import async_engine
from common.database.postgres_models import JobStatus, MinuteVersion, Transcription
from common.services.minute_handler_service import MinuteHandlerService
from common.workflows import minute_version as minute_wf
from common.workflows import transcription as wf
from common.workflows.activities import edit_minute, fail_minute, generate_minute, summarise
from tests.test_temporal_transcription_workflow import _activities, _workers


@pytest.mark.asyncio(loop_scope="session")
@pytest.mark.parametrize("kind", ["generate", "edit", "summary"])
async def test_exhausted_llm_retries_mark_minute_failed(minute_version_setup, monkeypatch, kind):
    transcription_id = minute_version_setup["transcription_id"]
    minute_id = minute_version_setup["minute_id"]
    version_id = minute_version_setup["minute_version_id"]
    llm = AsyncMock(side_effect=httpx.ReadTimeout("LLM unavailable"))
    monkeypatch.setattr(MinuteHandlerService, "generate_minutes", llm)
    monkeypatch.setattr(MinuteHandlerService, "edit_minutes_with_ai", llm)
    monkeypatch.setattr("common.services.minute_handler_service.capture_event", lambda *_args: None)

    by_queue = _activities([])
    by_queue[wf.LLM_TASK_QUEUE] = by_queue[wf.LLM_TASK_QUEUE][:2] + [
        generate_minute.generate_minute,
        edit_minute.edit_minute,
        summarise.summarise,
    ]
    by_queue[wf.TASK_QUEUE] = [by_queue[wf.TASK_QUEUE][0], fail_minute.fail_minute_version, fail_minute.fail_summarise]
    async with await WorkflowEnvironment.start_time_skipping() as env:
        workers = _workers(
            env.client,
            by_queue,
            workflows=[wf.TranscriptionWorkflow, minute_wf.MinuteGenerationWorkflow, minute_wf.MinuteEditWorkflow],
        )
        async with workers[0], workers[1], workers[2]:
            if kind == "summary":
                outcome = await env.client.execute_workflow(
                    wf.TranscriptionWorkflow.run, str(minute_id), id=str(uuid.uuid4()), task_queue=wf.TASK_QUEUE
                )
                assert outcome[wf.SUMMARISE].startswith("failed:")
            else:
                run = minute_wf.MinuteGenerationWorkflow.run if kind == "generate" else minute_wf.MinuteEditWorkflow.run
                arg = (
                    str(version_id)
                    if kind == "generate"
                    else minute_wf.MinuteEditInput(str(version_id), str(version_id))
                )
                with pytest.raises(WorkflowFailureError):
                    await env.client.execute_workflow(run, arg, id=str(uuid.uuid4()), task_queue=wf.TASK_QUEUE)
    assert llm.await_count == wf.LLM_RETRY.maximum_attempts
    async with AsyncSession(async_engine) as session:
        version = await session.get(MinuteVersion, version_id)
        assert version.status == JobStatus.FAILED
        assert "LLM unavailable" in version.error
        assert (await session.get(Transcription, transcription_id)).status == JobStatus.COMPLETED


@pytest.mark.asyncio(loop_scope="session")
async def test_activity_timeouts_finalise_minute(minute_version_setup, monkeypatch):
    version_id = minute_version_setup["minute_version_id"]

    async def _hang(*_args):
        await asyncio.Event().wait()

    monkeypatch.setattr(MinuteHandlerService, "generate_minutes", _hang)
    monkeypatch.setattr(minute_wf, "MINUTE_VERSION_TIMEOUT", timedelta(milliseconds=20))
    monkeypatch.setattr(minute_wf, "LLM_RETRY", RetryPolicy(maximum_attempts=2))
    async with await WorkflowEnvironment.start_time_skipping() as env:  # noqa: SIM117
        async with (
            Worker(
                env.client,
                task_queue=wf.TASK_QUEUE,
                workflows=[minute_wf.MinuteGenerationWorkflow],
                activities=[fail_minute.fail_minute_version],
                workflow_runner=UnsandboxedWorkflowRunner(),
            ),
            Worker(env.client, task_queue=wf.LLM_TASK_QUEUE, activities=[generate_minute.generate_minute]),
        ):
            with pytest.raises(WorkflowFailureError):
                await asyncio.wait_for(
                    env.client.execute_workflow(
                        minute_wf.MinuteGenerationWorkflow.run,
                        str(version_id),
                        id=str(uuid.uuid4()),
                        task_queue=wf.TASK_QUEUE,
                    ),
                    timeout=15,
                )
    async with AsyncSession(async_engine) as session:
        version = await session.get(MinuteVersion, version_id)
        assert version.status == JobStatus.FAILED
        assert version.error


@pytest.mark.asyncio(loop_scope="session")
@pytest.mark.parametrize("status", list(JobStatus))
async def test_minute_failure_write_preserves_terminal_rows(minute_version_setup, status):
    version_id = minute_version_setup["minute_version_id"]
    async with AsyncSession(async_engine) as session:
        version = await session.get(MinuteVersion, version_id)
        version.status = status
        version.html_content = "saved content"
        version.error = "original error"
        await session.commit()
    applied = MinuteHandlerService.record_minute_version_failure(version_id, "retries exhausted")
    unfinished = status in (JobStatus.AWAITING_START, JobStatus.IN_PROGRESS)
    assert applied is unfinished
    async with AsyncSession(async_engine) as session:
        version = await session.get(MinuteVersion, version_id)
        assert version.status == (JobStatus.FAILED if unfinished else status)
        assert version.html_content == "saved content"
        assert version.error == ("retries exhausted" if unfinished else "original error")

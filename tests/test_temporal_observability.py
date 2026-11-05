"""Exercise indexed starts, metadata upserts and visibility queries on a real local server."""

import asyncio
import uuid

import pytest
from temporalio import activity
from temporalio.client import WorkflowFailureError
from temporalio.converter import DataConverter
from temporalio.testing import WorkflowEnvironment
from temporalio.worker import Replayer, UnsandboxedWorkflowRunner, Worker

from backend.utils import temporal
from common.workflows import minute_version as minute_wf
from common.workflows import search_attributes as sa
from common.workflows import transcription as wf
from tests.test_temporal_transcription_workflow import _activities, _workers


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("upload_size_bytes", "stt_fails"), [(None, False), (0, False), (985225, False), (985225, True)]
)
async def test_workflows_are_searchable_by_ids_with_audio_metrics_in_memo(monkeypatch, stt_fails, upload_size_bytes):
    user_id, transcription_id, minute_id, initial_version_id, generated_version_id, edited_version_id = [
        uuid.uuid4() for _ in range(6)
    ]
    audio = wf.PreparedAudio(
        duration_seconds=7200.0,
        upload_size_bytes=upload_size_bytes,
    )
    by_queue = _activities([], audio=audio, fail=frozenset({wf.TRANSCRIBE}) if stt_fails else frozenset())

    @activity.defn(name=minute_wf.GENERATE_MINUTE)
    async def generate_minute(_version_id: str) -> None:
        pass

    @activity.defn(name=minute_wf.EDIT_MINUTE)
    async def edit_minute(_params: minute_wf.MinuteEditInput) -> None:
        pass

    by_queue[wf.LLM_TASK_QUEUE] += [generate_minute, edit_minute]
    workflows = [wf.TranscriptionWorkflow, minute_wf.MinuteGenerationWorkflow, minute_wf.MinuteEditWorkflow]
    attributes = [
        sa.USER_ID,
        sa.TRANSCRIPTION_ID,
        sa.MINUTE_ID,
        sa.MINUTE_VERSION_ID,
    ]
    async with await WorkflowEnvironment.start_local(search_attributes=attributes) as env:
        monkeypatch.setattr(temporal, "get_temporal_client", lambda: asyncio.sleep(0, result=env.client))
        workers = _workers(env.client, by_queue, workflows=workflows)
        async with workers[0], workers[1], workers[2]:
            await temporal.start_transcription_workflow(
                transcription_id, minute_id, user_id=user_id, minute_version_id=initial_version_id
            )
            metadata = {"user_id": user_id, "transcription_id": transcription_id, "minute_id": minute_id}
            await temporal.start_minute_generation_workflow(generated_version_id, **metadata)
            await temporal.start_minute_edit_workflow(edited_version_id, generated_version_id, **metadata)
            handles = [
                env.client.get_workflow_handle(wf.workflow_id(str(transcription_id))),
                env.client.get_workflow_handle(minute_wf.workflow_id(str(generated_version_id))),
                env.client.get_workflow_handle(minute_wf.workflow_id(str(edited_version_id))),
            ]
            results = await asyncio.gather(*(handle.result() for handle in handles), return_exceptions=True)
            expected_type = WorkflowFailureError if stt_fails else dict
            assert isinstance(results[0], expected_type)
            assert results[1:] == [None, None]
        for handle, version_id in zip(
            handles, [initial_version_id, generated_version_id, edited_version_id], strict=True
        ):
            description = await handle.describe()
            assert description.typed_search_attributes[sa.USER_ID] == str(user_id)
            assert description.typed_search_attributes[sa.TRANSCRIPTION_ID] == str(transcription_id)
            assert description.typed_search_attributes[sa.MINUTE_ID] == str(minute_id)
            assert description.typed_search_attributes[sa.MINUTE_VERSION_ID] == str(version_id)
            assert {"UploadSizeMb", "AudioUploadSizeMb", "AudioDurationSeconds"}.isdisjoint(
                key.name for key, _ in description.typed_search_attributes
            )
            if handle != handles[0]:
                assert await description.memo() == {}
        transcription = await handles[0].describe()
        expected_memo = {"AudioDurationSeconds": audio.duration_seconds}
        if upload_size_bytes is not None:
            expected_memo["AudioUploadSizeMb"] = pytest.approx(upload_size_bytes / 1_000_000)
        assert await transcription.memo() == expected_memo
        history = await handles[0].fetch_history()
        assert sum(event.HasField("workflow_properties_modified_event_attributes") for event in history.events) == 1
        queries = [
            (f"UserId = '{user_id}'", {handle.id for handle in handles}),
            (f"TranscriptionId = '{transcription_id}'", {handle.id for handle in handles}),
            (f"MinuteId = '{minute_id}'", {handle.id for handle in handles}),
            (f"MinuteVersionId = '{initial_version_id}'", {handles[0].id}),
            (f"MinuteVersionId = '{edited_version_id}'", {handles[2].id}),
        ]
        for query, expected in queries:
            for _ in range(100):
                found = {execution.id async for execution in env.client.list_workflows(query)}
                if found == expected:
                    break
                await asyncio.sleep(0.1)  # visibility indexing is asynchronous
            assert found == expected, query
        await Replayer(workflows=[wf.TranscriptionWorkflow]).replay_workflow(history)


@pytest.mark.asyncio
async def test_older_audio_preparation_result_remains_readable():
    payloads = await DataConverter.default.encode([{"duration_seconds": 7200.0}])
    assert await DataConverter.default.decode(payloads, [wf.PreparedAudio]) == [
        wf.PreparedAudio(duration_seconds=7200.0)
    ]


@pytest.mark.asyncio
async def test_history_without_audio_memo_replays(monkeypatch):
    """Generate the pre-memo command sequence, then replay it with the new worker."""
    async with await WorkflowEnvironment.start_time_skipping() as env:
        with monkeypatch.context() as legacy:
            legacy.setattr(wf.workflow, "patched", lambda _patch_id: False)
            workers = [
                Worker(
                    env.client,
                    task_queue=queue,
                    activities=activities,
                    workflows=[wf.TranscriptionWorkflow] if queue == wf.TASK_QUEUE else [],
                    workflow_runner=UnsandboxedWorkflowRunner(),
                )
                for queue, activities in _activities([], audio=wf.PreparedAudio(duration_seconds=7200.0)).items()
            ]
            async with workers[0], workers[1], workers[2]:
                handle = await env.client.start_workflow(
                    wf.TranscriptionWorkflow.run, str(uuid.uuid4()), id=str(uuid.uuid4()), task_queue=wf.TASK_QUEUE
                )
                await handle.result()
                assert await (await handle.describe()).memo() == {}
                history = await handle.fetch_history()
    await Replayer(workflows=[wf.TranscriptionWorkflow]).replay_workflow(history)


@pytest.mark.asyncio
async def test_status_page_audio_memo_history_replays(monkeypatch):
    """Keep the old status-page patch marker and Memo command readable after merging main."""
    patched = wf.workflow.patched
    async with await WorkflowEnvironment.start_time_skipping() as env:
        with monkeypatch.context() as legacy:
            legacy.setattr(
                wf.workflow,
                "patched",
                lambda patch_id: False if patch_id == "transcription-audio-memo" else patched(patch_id),
            )
            workers = [
                Worker(
                    env.client,
                    task_queue=queue,
                    activities=activities,
                    workflows=[wf.TranscriptionWorkflow] if queue == wf.TASK_QUEUE else [],
                    workflow_runner=UnsandboxedWorkflowRunner(),
                )
                for queue, activities in _activities([]).items()
            ]
            async with workers[0], workers[1], workers[2]:
                handle = await env.client.start_workflow(
                    wf.TranscriptionWorkflow.run, str(uuid.uuid4()), id=str(uuid.uuid4()), task_queue=wf.TASK_QUEUE
                )
                await handle.result()
                assert await (await handle.describe()).memo() == {"audio_seconds": 7200.0}
                history = await handle.fetch_history()
    await Replayer(workflows=[wf.TranscriptionWorkflow]).replay_workflow(history)

"""Only closed or missing workflows may have their database rows reset for a retry."""

import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest
from temporalio.client import WorkflowExecutionStatus
from temporalio.service import RPCError, RPCStatusCode

from backend.utils import temporal
from common.workflows.transcription import workflow_id


@pytest.mark.asyncio
@pytest.mark.parametrize("language", ["en", "cy"])
async def test_start_transcription_passes_language_to_workflow_without_database(monkeypatch, language):
    transcription_id, minute_id = uuid.uuid4(), uuid.uuid4()
    client = SimpleNamespace(start_workflow=AsyncMock())
    monkeypatch.setattr(temporal, "get_temporal_client", AsyncMock(return_value=client))
    await temporal.start_transcription_workflow(transcription_id, minute_id, language)
    client.start_workflow.assert_awaited_once_with(
        temporal.TranscriptionWorkflow.run,
        args=(str(minute_id), language),
        id=workflow_id(str(transcription_id)),
        task_queue=temporal.TASK_QUEUE,
    )


@pytest.mark.asyncio
@pytest.mark.parametrize("status", list(WorkflowExecutionStatus))
async def test_transcription_workflow_running_checks_latest_run(monkeypatch, status):
    transcription_id = uuid.uuid4()
    describe = AsyncMock(return_value=SimpleNamespace(status=status))
    client = Mock()
    client.get_workflow_handle.return_value.describe = describe
    monkeypatch.setattr(temporal, "get_temporal_client", AsyncMock(return_value=client))
    assert await temporal.transcription_workflow_running(transcription_id) is (
        status == WorkflowExecutionStatus.RUNNING
    )
    client.get_workflow_handle.assert_called_once_with(workflow_id(str(transcription_id)))


@pytest.mark.asyncio
@pytest.mark.parametrize("status", [RPCStatusCode.NOT_FOUND, RPCStatusCode.UNAVAILABLE])
async def test_only_missing_workflows_allow_retry_on_rpc_error(monkeypatch, status):
    error = RPCError("workflow unavailable", status, b"")
    client = Mock()
    client.get_workflow_handle.return_value.describe = AsyncMock(side_effect=error)
    monkeypatch.setattr(temporal, "get_temporal_client", AsyncMock(return_value=client))
    if status == RPCStatusCode.NOT_FOUND:
        assert await temporal.transcription_workflow_running(uuid.uuid4()) is False
    else:
        with pytest.raises(RPCError):
            await temporal.transcription_workflow_running(uuid.uuid4())

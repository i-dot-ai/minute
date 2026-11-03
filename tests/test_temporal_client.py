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


@pytest.mark.asyncio
@pytest.mark.parametrize("status", [RPCStatusCode.NOT_FOUND, RPCStatusCode.UNAVAILABLE])
async def test_indexed_start_still_only_retries_namespace_not_found(monkeypatch, status):
    error = RPCError("start failed", status, b"")
    client = SimpleNamespace(start_workflow=AsyncMock(side_effect=[error, None]))
    sleep = AsyncMock()
    monkeypatch.setattr(temporal, "get_temporal_client", AsyncMock(return_value=client))
    monkeypatch.setattr(temporal.asyncio, "sleep", sleep)
    ids = [uuid.uuid4() for _ in range(4)]
    if status == RPCStatusCode.NOT_FOUND:
        await temporal.start_transcription_workflow(ids[0], ids[1], user_id=ids[2], minute_version_id=ids[3])
        assert client.start_workflow.await_count == 2
        assert client.start_workflow.await_args_list[0] == client.start_workflow.await_args_list[1]
        sleep.assert_awaited_once()
    else:
        with pytest.raises(RPCError):
            await temporal.start_transcription_workflow(ids[0], ids[1], user_id=ids[2], minute_version_id=ids[3])
        client.start_workflow.assert_awaited_once()
        sleep.assert_not_awaited()

# pyright: reportPrivateUsage=false
# Tests intentionally exercise private helpers of the module under test.
"""Unit tests for consumer guards that do not need external services."""

from uuid import uuid4

import pytest

from common.services.messaging import Message
from common.types import TaskType, WorkerMessage
from worker.consumer import Consumer
from worker.signal_handler import SignalHandler


class FakeQueue:
    def __init__(self) -> None:
        self.dead_lettered: list[dict] = []
        self.acked: list[str] = []
        self.visibility_set: list[tuple[str, int]] = []

    def receive_message(self) -> Message | None:
        return None

    def receive_messages(self, max_messages: int) -> list[Message]:  # noqa: ARG002
        return []

    def publish_message(self, message: dict) -> None:
        pass

    def ack_message(self, receipt_handle: str) -> None:
        self.acked.append(receipt_handle)

    def set_visibility(self, receipt_handle: str, visibility_seconds: int) -> None:
        self.visibility_set.append((receipt_handle, visibility_seconds))

    def dead_letter_message(self, message: dict, receipt_handle: str) -> None:  # noqa: ARG002
        self.dead_lettered.append(message)

    def purge_messages(self) -> None:
        pass


def _consumer(queue: FakeQueue) -> Consumer:
    # Consumer takes the queue interface; FakeQueue satisfies it structurally.
    return Consumer(queue, SignalHandler())


def _message(body: dict) -> Message:
    return Message(body=body, receipt_handle="receipt")


def test_consumer_builds_the_two_phase_semaphores():
    """Fairness guard: transcription and LLM phases have separate capacity, so eight
    long transcriptions can never starve edits."""
    consumer = _consumer(FakeQueue())
    assert consumer.transcription_slot._value > 0
    assert consumer.llm_slot._value > 0
    assert consumer.transcription_slot is not consumer.llm_slot


@pytest.mark.asyncio
async def test_edit_message_without_source_data_is_deadlettered():
    queue = FakeQueue()
    consumer = _consumer(queue)
    body = WorkerMessage(id=uuid4(), type=TaskType.EDIT, data=None).model_dump(mode="json")

    await consumer._process(_message(body))

    assert queue.dead_lettered == [body]
    assert queue.acked == []


@pytest.mark.asyncio
async def test_unparseable_body_is_deadlettered():
    """A body that fails WorkerMessage validation can never be processed, so it is
    dead-lettered on arrival instead of being rehidden forever."""
    queue = FakeQueue()
    consumer = _consumer(queue)
    body = {"type": 99}

    await consumer._process(_message(body))

    assert queue.dead_lettered == [body]
    assert queue.acked == []


@pytest.mark.asyncio
async def test_handled_job_deletes_the_message(monkeypatch):
    """A handled job ("delete", success or recorded failure) is acked, not requeued."""

    async def handled(*_args, **_kwargs):
        return "delete"

    monkeypatch.setattr("worker.consumer.generate_minute_version", handled)
    queue = FakeQueue()
    consumer = _consumer(queue)
    body = WorkerMessage(id=uuid4(), type=TaskType.MINUTE).model_dump(mode="json")

    await consumer._process(_message(body))

    assert queue.acked == ["receipt"]
    assert queue.visibility_set == []


@pytest.mark.asyncio
async def test_job_owned_by_another_worker_is_rehidden(monkeypatch):
    """When the workflow reports the job is owned elsewhere ("rehide"), the message is
    hidden (visibility extended) and NOT acked, so it is retried later."""

    async def rehide(*_args, **_kwargs):
        return "rehide"

    monkeypatch.setattr("worker.consumer.generate_minute_version", rehide)
    queue = FakeQueue()
    consumer = _consumer(queue)
    body = WorkerMessage(id=uuid4(), type=TaskType.MINUTE).model_dump(mode="json")

    await consumer._process(_message(body))

    assert queue.acked == []
    assert queue.visibility_set == [("receipt", consumer.visibility_seconds)]


@pytest.mark.asyncio
async def test_crash_rehides_without_acking(monkeypatch):
    """An unexpected exception (nothing recorded in the DB) must not drop the job: the
    message is hidden and left to redeliver, never acked."""

    async def boom(*_args, **_kwargs):
        msg = "unexpected"
        raise RuntimeError(msg)

    monkeypatch.setattr("worker.consumer.generate_minute_version", boom)
    queue = FakeQueue()
    consumer = _consumer(queue)
    body = WorkerMessage(id=uuid4(), type=TaskType.MINUTE).model_dump(mode="json")

    await consumer._process(_message(body))

    assert queue.acked == []
    assert queue.visibility_set == [("receipt", consumer.visibility_seconds)]

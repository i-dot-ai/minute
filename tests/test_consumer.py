"""Unit tests for consumer guards that do not need external services."""

from uuid import uuid4

import pytest

from common.types import TaskType, WorkerMessage
from worker.consumer import Consumer
from worker.signal_handler import SignalHandler


class FakeQueue:
    name = "sqs"

    def __init__(self, *args, **kwargs) -> None:  # noqa: ARG002
        self.deadlettered: list[WorkerMessage] = []
        self.completed: list[str] = []
        self.extended: list[tuple[str, int]] = []

    def receive_message(self, max_messages: int = 10):  # noqa: ARG002
        return []

    def publish_message(self, message: WorkerMessage) -> None:
        pass

    def complete_message(self, receipt_handle) -> None:
        self.completed.append(receipt_handle)

    def extend_message(self, receipt_handle, visibility_seconds: int) -> None:
        self.extended.append((receipt_handle, visibility_seconds))

    def deadletter_message(self, message: WorkerMessage, receipt_handle) -> None:  # noqa: ARG002
        self.deadlettered.append(message)

    def abandon_message(self, receipt_handle) -> None:
        pass

    def purge_messages(self) -> None:
        pass


def test_consumer_builds_the_two_phase_semaphores():
    """Fairness guard: transcription and LLM phases have separate capacity, so eight
    long transcriptions can never starve edits."""
    consumer = Consumer(FakeQueue(), SignalHandler())
    assert consumer.transcription_slot._value > 0
    assert consumer.llm_slot._value > 0
    assert consumer.transcription_slot is not consumer.llm_slot


@pytest.mark.asyncio
async def test_edit_message_without_source_data_is_deadlettered():
    queue = FakeQueue()
    consumer = Consumer(queue, SignalHandler())
    message = WorkerMessage(id=uuid4(), type=TaskType.EDIT, data=None)

    await consumer._process(message, "receipt")

    assert queue.deadlettered == [message]
    assert queue.completed == []


@pytest.mark.asyncio
async def test_unknown_task_type_is_deadlettered():
    queue = FakeQueue()
    consumer = Consumer(queue, SignalHandler())
    message = WorkerMessage.model_construct(id=uuid4(), type=99, data=None)

    await consumer._process(message, "receipt")

    assert queue.deadlettered == [message]

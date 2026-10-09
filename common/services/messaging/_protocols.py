from typing import NamedTuple, Protocol


class Message(NamedTuple):
    body: dict
    receipt_handle: str


class Queue(Protocol):
    """Contract for the worker queue (receive, complete, retry/hide, deadletter, purge).

    Structural: the SQS implementation and test doubles both conform.
    """

    def publish_message(self, message: dict) -> None:
        """Enqueue a job message.

        :param message: The job to enqueue.
        """
        ...

    def receive_message(self) -> Message | None:
        """Long-poll for a single job.

        :returns: The received message, or ``None`` if the queue was empty.
        """
        ...

    def receive_messages(self, max_messages: int) -> list[Message]:
        """Long-poll for up to ``max_messages`` jobs.

        :param max_messages: Maximum number of messages to fetch.
        :returns: Received messages paired with their receipt handles.
        """
        ...

    def set_visibility(self, receipt_handle: str, visibility_seconds: int) -> None:
        """Keep a message invisible for another ``visibility_seconds``.

        :param receipt_handle: Handle of the message to hide.
        :param visibility_seconds: Additional invisibility window.
        """
        ...

    def ack_message(self, receipt_handle: str) -> None:
        """Delete a handled message.

        :param receipt_handle: Handle of the message to delete.
        """
        ...

    def dead_letter_message(self, message: dict, receipt_handle: str) -> None:
        """Move a poison message to the dead-letter queue.

        :param message: The message to dead-letter.
        :param receipt_handle: Handle of the source message.
        """
        ...

    def purge_messages(self) -> None:
        """Delete every message currently on the queue."""
        ...

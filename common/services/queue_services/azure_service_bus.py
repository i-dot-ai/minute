import logging
from contextlib import contextmanager
from typing import Any

from azure.servicebus import ServiceBusClient, ServiceBusMessage

from common.services.queue_services.base import QueueService
from common.settings import get_settings
from common.types import WorkerMessage

settings = get_settings()
logger = logging.getLogger(__name__)


@contextmanager
def get_sb_client():
    with ServiceBusClient.from_connection_string(settings.AZURE_SB_CONNECTION_STRING) as sb_client:
        yield sb_client


class AzureServiceBusQueueService(QueueService):
    name = "azure_service_bus"

    def __init__(
        self,
        polling_interval: int = 20,
    ):
        self.polling_interval = polling_interval
        self.queue_name = settings.QUEUE_NAME

    def __reduce__(self):
        """Required so that Ray can deserialize the queue service by instantiated a new one."""
        deserializer = AzureServiceBusQueueService
        serialized_data = ("queue_service",)
        return deserializer, serialized_data

    def receive_message(self) -> list[tuple[WorkerMessage, Any]]:
        out = []
        with (
            get_sb_client() as client,
            client.get_queue_receiver(self.queue_name) as receiver,
        ):
            messages = receiver.receive_messages(max_wait_time=self.polling_interval)

            for message in messages:
                try:
                    worker_message = WorkerMessage.model_validate_json(str(message))
                    receiver.renew_message_lock(message, timeout=1800.0)
                    out.append((worker_message, message))
                except Exception:
                    logger.exception("failed to process message")
        return out

    def publish_message(self, message: WorkerMessage):
        with get_sb_client() as client, client.get_queue_sender(self.queue_name) as sender:
            sender.send_messages([ServiceBusMessage(message.model_dump_json())])

    def complete_message(self, receipt_handle: Any):
        with (
            get_sb_client() as client,
            client.get_queue_receiver(self.queue_name) as receiver,
        ):
            receiver.complete_message(receipt_handle)

    def deadletter_message(self, message: WorkerMessage, receipt_handle: Any):  # noqa: ARG002
        with (
            get_sb_client() as client,
            client.get_queue_receiver(self.queue_name) as receiver,
        ):
            receiver.dead_letter_message(receipt_handle)

    def abandon_message(self, receipt_handle: Any):
        with (
            get_sb_client() as client,
            client.get_queue_receiver(self.queue_name) as receiver,
        ):
            receiver.abandon_message(receipt_handle)

    def purge_messages(self):
        with (
            get_sb_client() as client,
            client.get_queue_receiver(self.queue_name) as receiver,
        ):
            for msg in receiver:
                receiver.abandon_message(msg)

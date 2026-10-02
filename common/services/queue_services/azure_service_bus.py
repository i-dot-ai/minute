import logging
from typing import Any, Generic

from azure.servicebus import ServiceBusClient, ServiceBusMessage

from common.services.queue_services.base import MessageT, QueueService
from common.settings import get_settings
from common.types import WorkerMessage

settings = get_settings()
logger = logging.getLogger(__name__)


class AzureServiceBusQueueService(QueueService[MessageT], Generic[MessageT]):
    name = "azure_service_bus"

    def __init__(
        self,
        queue_name: str,
        deadletter_queue_name: str | None = None,  # noqa: ARG002
        polling_interval: int = 20,
        message_model: type[MessageT] = WorkerMessage,
    ):
        self.polling_interval = polling_interval
        self.queue_name = queue_name
        self.message_model = message_model
        if not settings.AZURE_SB_CONNECTION_STRING:
            msg = "AZURE_SB_CONNECTION_STRING is required for Azure Service Bus"
            raise ValueError(msg)
        self.client = ServiceBusClient.from_connection_string(settings.AZURE_SB_CONNECTION_STRING)
        self.receiver = self.client.get_queue_receiver(self.queue_name)
        self.receiver.__enter__()

    def __reduce__(self):
        """Required so that Ray can deserialize the queue service by instantiated a new one."""
        return AzureServiceBusQueueService, (self.queue_name, None, self.polling_interval, self.message_model)

    def receive_message(self, max_messages: int = 10) -> list[tuple[MessageT, Any]]:
        out = []
        messages = self.receiver.receive_messages(max_message_count=max_messages, max_wait_time=self.polling_interval)
        for message in messages:
            try:
                worker_message = self.message_model.model_validate_json(str(message))
            except Exception:
                logger.exception("invalid message payload; moving it to the dead-letter queue")
                self.receiver.dead_letter_message(message, reason="Invalid message payload")
                continue
            self.receiver.renew_message_lock(message)
            out.append((worker_message, message))
        return out

    def publish_message(self, message: MessageT):
        with self.client.get_queue_sender(self.queue_name) as sender:
            sender.send_messages([ServiceBusMessage(message.model_dump_json())])

    def complete_message(self, receipt_handle: Any):
        self.receiver.complete_message(receipt_handle)

    def deadletter_message(self, message: MessageT, receipt_handle: Any):  # noqa: ARG002
        self.receiver.dead_letter_message(receipt_handle)

    def abandon_message(self, receipt_handle: Any):
        self.receiver.abandon_message(receipt_handle)

    def purge_messages(self):
        for msg in self.receiver:
            self.receiver.complete_message(msg)

    def close(self, *, force: bool = False):
        if not force:
            self.receiver.__exit__(None, None, None)
        self.client.close()

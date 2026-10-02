import logging
from typing import Any, Generic

import boto3

from common.services.queue_services.base import MessageT, QueueService
from common.settings import get_settings
from common.types import WorkerMessage

settings = get_settings()
logger = logging.getLogger(__name__)


def get_sqs_client():
    if settings.USE_MINISTACK and settings.ENVIRONMENT == "local":
        return boto3.client(
            "sqs",
            aws_access_key_id="YOUR_ACCESS_KEY_ID",
            aws_secret_access_key="YOUR_SECRET_ACCESS_KEY",  # noqa: S106
            region_name="eu-west-2",
            endpoint_url=settings.MINISTACK_URL,
        )

    return boto3.client("sqs")


class SQSQueueService(QueueService[MessageT], Generic[MessageT]):
    name = "sqs"

    def __init__(
        self,
        queue_name: str,
        deadletter_queue_name: str,
        polling_interval: int = 20,
        message_model: type[MessageT] = WorkerMessage,
    ):
        self.queue_name = queue_name
        self.deadletter_queue_name = deadletter_queue_name
        self.sqs = get_sqs_client()
        self.queue_url = self.sqs.get_queue_url(QueueName=self.queue_name)["QueueUrl"]
        self.dead_letter_queue_url = self.sqs.get_queue_url(QueueName=self.deadletter_queue_name)["QueueUrl"]
        self.polling_interval = polling_interval
        self.message_model = message_model

    def __reduce__(self):
        """Required so that Ray can deserialize the queue service by instantiated a new one."""
        return SQSQueueService, (self.queue_name, self.deadletter_queue_name, self.polling_interval, self.message_model)

    def receive_message(self, max_messages: int = 10) -> list[tuple[MessageT, Any]]:
        response = self.sqs.receive_message(
            QueueUrl=self.queue_url,
            MaxNumberOfMessages=max_messages,
            WaitTimeSeconds=self.polling_interval,  # Long polling
        )

        messages = response.get("Messages", [])
        out = []
        for message in messages:
            receipt_handle = message["ReceiptHandle"]
            try:
                worker_message = self.message_model.model_validate_json(message["Body"])
            except Exception:
                logger.exception("invalid message payload; moving it to the dead-letter queue")
                try:
                    self.sqs.send_message(QueueUrl=self.dead_letter_queue_url, MessageBody=message["Body"])
                    self.sqs.delete_message(QueueUrl=self.queue_url, ReceiptHandle=receipt_handle)
                except Exception:
                    logger.exception("failed to dead-letter invalid message payload")
                continue
            self.sqs.change_message_visibility(
                QueueUrl=self.queue_url,
                ReceiptHandle=receipt_handle,
                VisibilityTimeout=1800,
            )
            out.append((worker_message, receipt_handle))
        return out

    def publish_message(self, message: MessageT):
        self.sqs.send_message(QueueUrl=self.queue_url, MessageBody=message.model_dump_json())

    def complete_message(self, receipt_handle: Any):
        try:
            self.sqs.delete_message(QueueUrl=self.queue_url, ReceiptHandle=receipt_handle)
        except Exception:
            logger.exception("failed to complete message")
            raise

    def deadletter_message(self, message: MessageT, receipt_handle: Any):
        try:
            self.sqs.send_message(QueueUrl=self.dead_letter_queue_url, MessageBody=message.model_dump_json())
            self.sqs.delete_message(QueueUrl=self.queue_url, ReceiptHandle=receipt_handle)
        except self.sqs.exceptions.ReceiptHandleIsInvalid:
            logger.warning("ReceiptHandleIsInvalid raised when deadlettering message. Message=%s", message.model_dump())

    def abandon_message(self, receipt_handle: Any):
        try:
            self.sqs.change_message_visibility(
                QueueUrl=self.queue_url, ReceiptHandle=receipt_handle, VisibilityTimeout=0
            )
        except Exception:
            logger.exception("failed to abandon message")

    def purge_messages(self):
        self.sqs.purge_queue(QueueUrl=self.queue_url)

    def close(self, *, force: bool = False):  # noqa: ARG002
        self.sqs.close()

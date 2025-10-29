import logging
from typing import Any

import boto3

from common.services.queue_services.base import QueueService
from common.settings import get_settings
from common.types import WorkerMessage

settings = get_settings()
logger = logging.getLogger(__name__)


def get_sqs_client():
    if settings.USE_LOCALSTACK and settings.ENVIRONMENT == "local":
        return boto3.client(
            "sqs",
            endpoint_url=settings.LOCALSTACK_URL,
        )

    return boto3.client("sqs")


class SQSQueueService(QueueService):
    name = "sqs"

    def __init__(
        self,
        polling_interval: int = 20,
    ):
        self.sqs = get_sqs_client()
        self.queue_url = self.sqs.get_queue_url(QueueName=settings.QUEUE_NAME)["QueueUrl"]
        self.dead_letter_queue_url = self.sqs.get_queue_url(QueueName=settings.DEADLETTER_QUEUE_NAME)["QueueUrl"]
        self.polling_interval = polling_interval

    def __reduce__(self):
        """Required so that Ray can deserialize the queue service by instantiated a new one."""
        deserializer = SQSQueueService
        serialized_data = ("queue_service",)
        return deserializer, serialized_data

    def receive_message(self) -> list[tuple[WorkerMessage, Any]]:
        response = self.sqs.receive_message(
            QueueUrl=self.queue_url,
            MaxNumberOfMessages=10,
            WaitTimeSeconds=self.polling_interval,  # Long polling
        )

        messages = response.get("Messages", [])
        out = []
        for message in messages:
            receipt_handle = message["ReceiptHandle"]
            try:
                worker_message = WorkerMessage.model_validate_json(message["Body"])
                self.sqs.change_message_visibility(
                    QueueUrl=self.queue_url, ReceiptHandle=receipt_handle, VisibilityTimeout=1800
                )
                out.append((worker_message, receipt_handle))
            except Exception:
                logger.exception("failed to process message")
        return out

    def publish_message(self, message: WorkerMessage):
        self.sqs.send_message(QueueUrl=self.queue_url, MessageBody=message.model_dump_json())

    def complete_message(self, receipt_handle: Any):
        try:
            self.sqs.delete_message(QueueUrl=self.queue_url, ReceiptHandle=receipt_handle)
        except self.sqs.exceptions.ReceiptHandleIsInvalid:
            logger.warning("ReceiptHandleIsInvalid raised when completing message")

    def deadletter_message(self, message: WorkerMessage, receipt_handle: Any):
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
        except self.sqs.exceptions.ReceiptHandleIsInvalid:
            logger.warning("ReceiptHandleIsInvalid raised when abandoning message")

    def purge_messages(self):
        self.sqs.purge_queue(QueueUrl=self.queue_url)

import logging
from typing import Any

import boto3

from common.services.queue_services.base import QueueService
from common.settings import get_settings
from common.types import WorkerMessage

settings = get_settings()
logger = logging.getLogger(__name__)


# Any type used instead of SQSClient - mypy-boto3-sqs plugin should not be installed in production
def get_sqs_client() -> Any:
    if settings.USE_ELASTICMQ and settings.ENVIRONMENT.lower() in ["local", "test"]:
        return boto3.client(
            "sqs",
            aws_access_key_id="YOUR_ACCESS_KEY_ID",
            aws_secret_access_key="YOUR_SECRET_ACCESS_KEY",  # noqa: S106
            region_name="eu-west-2",
            endpoint_url=settings.ELASTICMQ_URL,
        )
    return boto3.client("sqs")


class SQSQueueService(QueueService):
    name = "sqs"

    def __init__(
        self,
        queue_name: str,
        deadletter_queue_name: str,
        polling_interval: int = 20,
    ):
        self.queue_name = queue_name
        self.deadletter_queue_name = deadletter_queue_name
        self.sqs = get_sqs_client()
        self.queue_url = self.sqs.get_queue_url(QueueName=self.queue_name)["QueueUrl"]
        self.dead_letter_queue_url = self.sqs.get_queue_url(QueueName=self.deadletter_queue_name)["QueueUrl"]
        self.polling_interval = polling_interval

    def __reduce__(self) -> tuple[type["SQSQueueService"], tuple[str, str]]:
        """Required so that Ray can deserialize the queue service by instantiated a new one."""
        return SQSQueueService, (self.queue_name, self.deadletter_queue_name)

    def receive_message(self, max_messages: int = 10) -> list[tuple[WorkerMessage, str]]:
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
                worker_message = WorkerMessage.model_validate_json(message["Body"])
                self.sqs.change_message_visibility(
                    QueueUrl=self.queue_url, ReceiptHandle=receipt_handle, VisibilityTimeout=1800
                )
                out.append((worker_message, receipt_handle))
            except Exception:
                logger.exception("failed to process message")
        return out

    def publish_message(self, message: WorkerMessage) -> None:
        self.sqs.send_message(QueueUrl=self.queue_url, MessageBody=message.model_dump_json())

    def complete_message(self, receipt_handle: str) -> None:
        try:
            self.sqs.delete_message(QueueUrl=self.queue_url, ReceiptHandle=receipt_handle)
        except self.sqs.exceptions.ReceiptHandleIsInvalid:
            logger.warning("ReceiptHandleIsInvalid raised when completing message")

    def deadletter_message(self, message: WorkerMessage, receipt_handle: str) -> None:
        try:
            self.sqs.send_message(QueueUrl=self.dead_letter_queue_url, MessageBody=message.model_dump_json())
            self.sqs.delete_message(QueueUrl=self.queue_url, ReceiptHandle=receipt_handle)
        except self.sqs.exceptions.ReceiptHandleIsInvalid:
            logger.warning("ReceiptHandleIsInvalid raised when deadlettering message. Message=%s", message.model_dump())

    def abandon_message(self, receipt_handle: str) -> None:
        try:
            self.sqs.change_message_visibility(
                QueueUrl=self.queue_url, ReceiptHandle=receipt_handle, VisibilityTimeout=0
            )
        except self.sqs.exceptions.ReceiptHandleIsInvalid:
            logger.warning("ReceiptHandleIsInvalid raised when abandoning message")

    def purge_messages(self) -> None:
        self.sqs.purge_queue(QueueUrl=self.queue_url)

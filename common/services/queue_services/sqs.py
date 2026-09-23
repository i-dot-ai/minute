import logging
from typing import Any

import boto3

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


class SQSQueueService:
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

    def receive_message(self, max_messages: int = 10) -> list[tuple[WorkerMessage, Any]]:
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

    def publish_message(self, message: WorkerMessage, delay_seconds: int = 0):
        # SQS caps DelaySeconds at 900 (15 minutes).
        delay_seconds = max(0, min(delay_seconds, 900))
        self.sqs.send_message(
            QueueUrl=self.queue_url,
            MessageBody=message.model_dump_json(),
            DelaySeconds=delay_seconds,
        )

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

    def get_queue_depth(self) -> dict[str, int]:
        """Return approximate message counts for the main and dead-letter queues.

        Useful for diagnostics: shows how many messages are waiting, in-flight
        (received but not yet deleted), or delayed, plus anything in the DLQ.
        """
        attrs = self.sqs.get_queue_attributes(
            QueueUrl=self.queue_url,
            AttributeNames=[
                "ApproximateNumberOfMessages",
                "ApproximateNumberOfMessagesNotVisible",
                "ApproximateNumberOfMessagesDelayed",
            ],
        ).get("Attributes", {})
        dlq_attrs = self.sqs.get_queue_attributes(
            QueueUrl=self.dead_letter_queue_url,
            AttributeNames=["ApproximateNumberOfMessages"],
        ).get("Attributes", {})
        return {
            "visible": int(attrs.get("ApproximateNumberOfMessages", 0)),
            "in_flight": int(attrs.get("ApproximateNumberOfMessagesNotVisible", 0)),
            "delayed": int(attrs.get("ApproximateNumberOfMessagesDelayed", 0)),
            "deadletter": int(dlq_attrs.get("ApproximateNumberOfMessages", 0)),
        }


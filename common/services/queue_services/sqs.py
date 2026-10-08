from typing import Any

import boto3

from common.services.queue_services.base import QueueService
from common.settings import get_settings, get_structured_logger
from common.types import WorkerMessage

slogger = get_structured_logger()
settings = get_settings()


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
        self.visibility_timeout = settings.JOB_VISIBILITY_TIMEOUT_SECS

    def __reduce__(self):
        """Required so that Ray can deserialize the queue service by instantiated a new one."""
        return SQSQueueService, (self.queue_name, self.deadletter_queue_name)

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
                    QueueUrl=self.queue_url, ReceiptHandle=receipt_handle, VisibilityTimeout=self.visibility_timeout
                )
                out.append((worker_message, receipt_handle))
            except Exception:
                slogger.exception("Failed to parse worker message")
        return out

    def publish_message(self, message: WorkerMessage):
        self.sqs.send_message(QueueUrl=self.queue_url, MessageBody=message.model_dump_json())

    def complete_message(self, receipt_handle: Any):
        try:
            self.sqs.delete_message(QueueUrl=self.queue_url, ReceiptHandle=receipt_handle)
        except self.sqs.exceptions.ReceiptHandleIsInvalid:
            slogger.warning("ReceiptHandleIsInvalid raised when completing message")

    def extend_message(self, receipt_handle: Any, visibility_seconds: int):
        try:
            self.sqs.change_message_visibility(
                QueueUrl=self.queue_url, ReceiptHandle=receipt_handle, VisibilityTimeout=visibility_seconds
            )
        except self.sqs.exceptions.ReceiptHandleIsInvalid:
            slogger.warning("ReceiptHandleIsInvalid raised when extending message")

    def deadletter_message(self, message: WorkerMessage, receipt_handle: Any):
        try:
            self.sqs.send_message(QueueUrl=self.dead_letter_queue_url, MessageBody=message.model_dump_json())
            self.sqs.delete_message(QueueUrl=self.queue_url, ReceiptHandle=receipt_handle)
        except self.sqs.exceptions.ReceiptHandleIsInvalid:
            slogger.warning(
                "ReceiptHandleIsInvalid raised when deadlettering message: {message}", message=str(message.model_dump())
            )

    def abandon_message(self, receipt_handle: Any):
        try:
            self.sqs.change_message_visibility(
                QueueUrl=self.queue_url, ReceiptHandle=receipt_handle, VisibilityTimeout=0
            )
        except self.sqs.exceptions.ReceiptHandleIsInvalid:
            slogger.warning("ReceiptHandleIsInvalid raised when abandoning message")

    def purge_messages(self):
        self.sqs.purge_queue(QueueUrl=self.queue_url)

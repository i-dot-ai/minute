import logging
from typing import Any

import boto3

from common.services.queue_services.base import QueueService
from common.settings import get_settings
from common.types import WorkerMessage

# In-flight window before SQS redelivers an unacked message. Bounded below by
# CLAIM_STALE_AFTER (3 min) so the first redelivery can always reclaim a crashed
# claimant's job. While a task runs, worker/lease_renewer.py keeps resetting this
# window, so long tasks are not redelivered; it lapses only when the worker dies.
VISIBILITY_TIMEOUT_SECONDS = 300

settings = get_settings()
logger = logging.getLogger(__name__)


def get_sqs_client():
    """Same AWS_* settings as storage: MiniStack locally, the ECS task role when deployed (all unset)."""
    return boto3.client(
        "sqs",
        aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
        region_name=settings.AWS_DEFAULT_REGION,
        endpoint_url=settings.AWS_ENDPOINT_URL,
    )


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
                    QueueUrl=self.queue_url, ReceiptHandle=receipt_handle, VisibilityTimeout=VISIBILITY_TIMEOUT_SECONDS
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

    def extend_message_lease(self, receipt_handle: Any) -> bool:
        """Reset the in-flight window for a message whose task is still running.

        Returns False when the receipt is no longer valid (the message was already
        completed or handed to another consumer), so the caller can stop renewing.
        """
        try:
            self.sqs.change_message_visibility(
                QueueUrl=self.queue_url, ReceiptHandle=receipt_handle, VisibilityTimeout=VISIBILITY_TIMEOUT_SECONDS
            )
        except self.sqs.exceptions.ReceiptHandleIsInvalid:
            logger.warning("ReceiptHandleIsInvalid raised when extending message lease")
            return False
        return True

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

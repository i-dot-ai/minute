import json

import boto3

from common.services.messaging._protocols import Message, Queue
from common.settings import get_settings

settings = get_settings()


class SQS(Queue):
    def __init__(
        self,
        queue_name: str,
        dl_queue_name: str,
        wait_time_seconds: int = 20,  # SQS long-polling maximum
        visibility_seconds: int = settings.JOB_VISIBILITY_TIMEOUT_SECS,
    ):
        client = boto3.client(
            "sqs",
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            region_name=settings.AWS_DEFAULT_REGION,
            endpoint_url=settings.AWS_ENDPOINT_URL,
        )

        queue_url = client.get_queue_url(QueueName=queue_name)["QueueUrl"]
        dl_queue_url = client.get_queue_url(QueueName=dl_queue_name)["QueueUrl"]

        self._client = client
        self._queue_url = queue_url
        self._dl_queue_url = dl_queue_url
        self._wait_time_seconds = wait_time_seconds
        self._visibility_seconds = visibility_seconds

    def receive_message(self) -> Message | None:
        if messages := self.receive_messages(max_messages=1):
            return messages[0]
        return None

    def receive_messages(self, max_messages: int) -> list[Message]:
        response = self._client.receive_message(
            QueueUrl=self._queue_url,
            MaxNumberOfMessages=max_messages,
            WaitTimeSeconds=self._wait_time_seconds,
        )

        messages: list[Message] = []
        for message in response.get("Messages", []):
            body = json.loads(message["Body"])
            receipt_handle = message["ReceiptHandle"]
            self._client.change_message_visibility(
                QueueUrl=self._queue_url,
                ReceiptHandle=receipt_handle,
                VisibilityTimeout=self._visibility_seconds,
            )
            messages.append(
                Message(
                    body=body,  # dict
                    receipt_handle=receipt_handle,
                )
            )
        return messages

    def publish_message(self, message: dict) -> None:
        self._client.send_message(
            QueueUrl=self._queue_url,
            MessageBody=json.dumps(message),
        )

    def ack_message(self, receipt_handle: str) -> None:
        self._client.delete_message(
            QueueUrl=self._queue_url,
            ReceiptHandle=receipt_handle,
        )

    def set_visibility(self, receipt_handle: str, visibility_seconds: int) -> None:
        self._client.change_message_visibility(
            QueueUrl=self._queue_url,
            ReceiptHandle=receipt_handle,
            VisibilityTimeout=visibility_seconds,
        )

    def dead_letter_message(self, message: dict, receipt_handle: str) -> None:
        self._client.send_message(
            QueueUrl=self._dl_queue_url,
            MessageBody=json.dumps(message),
        )
        self._client.delete_message(
            QueueUrl=self._queue_url,
            ReceiptHandle=receipt_handle,
        )

    def purge_messages(self):
        self._client.purge_queue(QueueUrl=self._queue_url)

import uuid
from unittest.mock import MagicMock, patch

from common.services.queue_services.sqs import SQSQueueService
from common.types import AudioWorkerMessage, TaskType, WorkerMessage


def _sqs_service(message_model):
    client = MagicMock()
    client.get_queue_url.side_effect = [
        {"QueueUrl": "https://sqs.example/main"},
        {"QueueUrl": "https://sqs.example/deadletter"},
    ]
    with patch("common.services.queue_services.sqs.get_sqs_client", return_value=client):
        service = SQSQueueService("main", "deadletter", polling_interval=0, message_model=message_model)
    return service, client


def test_sqs_deserializes_audio_worker_message():
    expected = AudioWorkerMessage(
        user_id=uuid.uuid4(),
        transcription_id=uuid.uuid4(),
        minute_id=uuid.uuid4(),
        s3_file_key="uploads/audio.wav",
    )
    service, client = _sqs_service(AudioWorkerMessage)
    client.receive_message.return_value = {
        "Messages": [{"Body": expected.model_dump_json(), "ReceiptHandle": "receipt"}]
    }

    assert service.receive_message() == [(expected, "receipt")]
    client.change_message_visibility.assert_called_once()


def test_sqs_rejects_wrong_schema_to_deadletter_queue():
    service, client = _sqs_service(AudioWorkerMessage)
    message = WorkerMessage(id=uuid.uuid4(), type=TaskType.TRANSCRIPTION)
    client.receive_message.return_value = {
        "Messages": [{"Body": message.model_dump_json(), "ReceiptHandle": "receipt"}]
    }

    assert service.receive_message() == []
    client.send_message.assert_called_once_with(
        QueueUrl="https://sqs.example/deadletter",
        MessageBody=message.model_dump_json(),
    )
    client.delete_message.assert_called_once_with(
        QueueUrl="https://sqs.example/main",
        ReceiptHandle="receipt",
    )

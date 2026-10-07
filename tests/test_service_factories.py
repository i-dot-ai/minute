import pytest

from common.services.queue_services import get_queue_service
from common.services.queue_services.sqs import SQSQueueService
from common.services.storage_services import S3StorageService, get_storage_service


def test_service_factories(monkeypatch):
    monkeypatch.setattr(SQSQueueService, "__init__", lambda _self, *_: None)

    assert isinstance(get_queue_service("sqs", "queue", "deadletter"), SQSQueueService)
    assert get_storage_service("s3") is S3StorageService

    with pytest.raises(ValueError, match="Invalid queue service name: azure"):
        get_queue_service("azure", "queue", "deadletter")
    with pytest.raises(ValueError, match="Invalid storage service name: azure"):
        get_storage_service("azure")

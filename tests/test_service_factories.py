import pytest

from common.services.storage_services import S3StorageService, get_storage_service


def test_service_factories():
    assert get_storage_service("s3") is S3StorageService

    with pytest.raises(ValueError, match="Invalid storage service name: azure"):
        get_storage_service("azure")

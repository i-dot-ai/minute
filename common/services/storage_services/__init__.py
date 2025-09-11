from .azure_blob import AzureBlobStorageService
from .base import StorageService
from .s3 import S3StorageService

storage_services = {S3StorageService.name: S3StorageService, AzureBlobStorageService.name: AzureBlobStorageService}


def get_storage_service(storage_service_name: str) -> StorageService:
    service = storage_services.get(storage_service_name)
    if not service:
        msg = f"Invalid storage service name: {storage_service_name}"
        raise ValueError(msg)
    return service

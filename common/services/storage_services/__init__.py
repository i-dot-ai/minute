from .base import StorageService

# Concrete backends are imported lazily inside get_storage_service so that a
# deployment only loads the SDK for the storage backend it is configured to use
# (e.g. an S3/local deployment must not import azure.storage.blob). This keeps
# provider-specific worker images from pulling in every storage SDK.


def get_storage_service(storage_service_name: str) -> type[StorageService]:
    if storage_service_name == "s3":
        from .s3 import S3StorageService

        return S3StorageService
    if storage_service_name == "azure_blob":
        from .azure_blob import AzureBlobStorageService

        return AzureBlobStorageService
    if storage_service_name == "local":
        from .local.local import LocalStorageService

        return LocalStorageService

    msg = f"Invalid storage service name: {storage_service_name}"
    raise ValueError(msg)

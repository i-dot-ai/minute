from backend.services.queue_services.azure_service_bus import AzureServiceBusQueueService
from backend.services.queue_services.base import QueueService
from backend.services.queue_services.sqs import SQSQueueService

queue_services = {
    SQSQueueService.name: SQSQueueService(),
    AzureServiceBusQueueService.name: AzureServiceBusQueueService(),
}


def get_queue_service(storage_service_name: str) -> QueueService:
    service = queue_services.get(storage_service_name)
    if not service:
        msg = f"Invalid storage service name: {storage_service_name}"
        raise ValueError(msg)
    return service

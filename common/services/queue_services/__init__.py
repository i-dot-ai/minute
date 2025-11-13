from common.services.queue_services.azure_service_bus import AzureServiceBusQueueService
from common.services.queue_services.base import QueueService
from common.services.queue_services.sqs import SQSQueueService

queue_services: dict[str, type[QueueService]] = {
    SQSQueueService.name: SQSQueueService,
    AzureServiceBusQueueService.name: AzureServiceBusQueueService,
}


def get_queue_service(queue_service_name: str, queue_name: str, deadletter_queue_name: str) -> QueueService:
    service = queue_services.get(queue_service_name)
    if not service:
        msg = f"Invalid storage service name: {queue_service_name}"
        raise ValueError(msg)
    return service(queue_name, deadletter_queue_name)

from typing import overload

from common.services.queue_services.azure_service_bus import AzureServiceBusQueueService
from common.services.queue_services.base import QueueService
from common.services.queue_services.sqs import SQSQueueService
from common.types import AudioWorkerMessage, WorkerMessage

queue_services: dict[str, type[QueueService]] = {
    SQSQueueService.name: SQSQueueService,
    AzureServiceBusQueueService.name: AzureServiceBusQueueService,
}


@overload
def get_queue_service(
    queue_service_name: str,
    queue_name: str,
    deadletter_queue_name: str,
    message_model: type[AudioWorkerMessage],
) -> QueueService[AudioWorkerMessage]: ...


@overload
def get_queue_service(
    queue_service_name: str,
    queue_name: str,
    deadletter_queue_name: str,
    message_model: type[WorkerMessage] = WorkerMessage,
) -> QueueService[WorkerMessage]: ...


def get_queue_service(
    queue_service_name: str,
    queue_name: str,
    deadletter_queue_name: str,
    message_model: type[AudioWorkerMessage] | type[WorkerMessage] = WorkerMessage,
) -> QueueService:
    service = queue_services.get(queue_service_name)
    if not service:
        msg = f"Invalid storage service name: {queue_service_name}"
        raise ValueError(msg)
    return service(queue_name, deadletter_queue_name, message_model=message_model)

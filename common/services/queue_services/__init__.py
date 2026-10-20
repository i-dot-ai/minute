from common.services.queue_services.base import QueueService
from common.services.queue_services.sqs import SQSQueueService

queue_services: dict[str, type[QueueService]] = {
    SQSQueueService.name: SQSQueueService,
}


def get_queue_service(queue_service_name: str, queue_name: str, deadletter_queue_name: str) -> QueueService:
    service = queue_services.get(queue_service_name)
    if not service:
        msg = f"Invalid queue service name: {queue_service_name}"
        raise ValueError(msg)
    return service(queue_name, deadletter_queue_name)

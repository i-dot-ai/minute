from common.services.queue_services.sqs import SQSQueueService


def get_queue_service(queue_name: str, deadletter_queue_name: str) -> SQSQueueService:
    return SQSQueueService(queue_name, deadletter_queue_name)

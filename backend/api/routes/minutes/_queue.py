from common.services.queue_services import get_queue_service
from common.settings import get_settings

settings = get_settings()

llm_queue_service = get_queue_service(
    settings.LLM_QUEUE_NAME,
    settings.LLM_DEADLETTER_QUEUE_NAME,
)

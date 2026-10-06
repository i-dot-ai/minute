import asyncio
from functools import cache

from audio_worker.handler import handle_message
from common.services.queue_services import get_queue_service
from common.services.queue_services.base import QueueService
from common.services.storage_services import get_storage_service as _get_storage_service
from common.services.storage_services.base import StorageService
from common.settings import get_settings, get_structured_logger
from common.signal_handler import SignalHandler
from common.types import AudioWorkerMessage, WorkerMessage

settings = get_settings()
slogger = get_structured_logger()


@cache
def get_storage_service() -> StorageService:
    return _get_storage_service(settings.STORAGE_SERVICE_NAME)


@cache
def get_input_queue() -> QueueService[AudioWorkerMessage]:
    return get_queue_service(
        queue_service_name=settings.QUEUE_SERVICE_NAME,
        queue_name=settings.AUDIO_QUEUE_NAME,
        deadletter_queue_name=settings.AUDIO_DEADLETTER_QUEUE_NAME,
        message_model=AudioWorkerMessage,
    )


@cache
def get_output_queue() -> QueueService[WorkerMessage]:
    return get_queue_service(
        queue_service_name=settings.QUEUE_SERVICE_NAME,
        queue_name=settings.TRANSCRIPTION_QUEUE_NAME,
        deadletter_queue_name=settings.TRANSCRIPTION_DEADLETTER_QUEUE_NAME,
        message_model=WorkerMessage,
    )


async def run() -> None:
    signal_handler = SignalHandler()
    input_queue = get_input_queue()
    output_queue = get_output_queue()

    try:
        while not signal_handler.signal_received:  # sigint/sigterm
            # Audio queue: WaitTimeSeconds=20
            if messages := input_queue.receive_message(max_messages=1):
                message, receipt_handle = messages[0]
                if signal_handler.signal_received:  # re-check
                    input_queue.abandon_message(receipt_handle)
                    return  # do not start, it will be interrupted
                try:
                    await handle_message(
                        message=message,
                        receipt_handle=receipt_handle,
                        input_queue=input_queue,
                        output_queue=output_queue,
                        storage_service=get_storage_service(),
                    )
                except Exception:
                    slogger.exception("Failed to mark audio message terminal; SQS will redeliver it")

    finally:
        input_queue.close()
        output_queue.close()


if __name__ == "__main__":
    asyncio.run(run())

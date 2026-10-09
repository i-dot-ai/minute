import asyncio

from common.sentry import init_sentry
from common.services.messaging import SQS
from common.settings import get_settings
from worker.consumer import Consumer
from worker.signal_handler import SignalHandler

if __name__ == "__main__":
    init_sentry()
    settings = get_settings()
    queue = SQS(settings.WORKER_QUEUE_NAME, settings.WORKER_DEADLETTER_QUEUE_NAME)
    consumer = Consumer(queue=queue, signal_handler=SignalHandler())
    asyncio.run(consumer.run())

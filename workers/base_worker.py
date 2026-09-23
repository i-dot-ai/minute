import asyncio
import logging
from abc import ABC, abstractmethod
from typing import Any

from common.services.queue_services.sqs import SQSQueueService
from common.types import WorkerMessage
from workers.signal_handler import SignalHandler

logger = logging.getLogger(__name__)


class PoisonMessageError(Exception):
    """Raised when a message can never be processed successfully and should be dead-lettered immediately.

    Any other exception is treated as transient: the message is abandoned (its visibility
    timeout is reset) so SQS redelivers it. After the queue's maxReceiveCount is exceeded,
    SQS moves it to the dead-letter queue automatically.
    """


class BaseWorker(ABC):
    """Base class for all worker types.

    Subclasses implement `process_message`. The base class owns the polling loop,
    concurrency, graceful shutdown and the completion / retry / dead-letter semantics.
    """

    # How many messages to pull (and process concurrently) per poll. Override per worker.
    max_messages: int = 1

    def __init__(self, input_queue_service: SQSQueueService, signal_handler: SignalHandler | None = None):
        self.input_queue_service = input_queue_service
        self.signal_handler = signal_handler or SignalHandler()

    @abstractmethod
    async def process_message(self, message: WorkerMessage) -> None:
        """Process a single message.

        Return normally to acknowledge (complete) the message. Raise `PoisonMessageError`
        to dead-letter immediately. Raise any other exception to abandon for redelivery.
        """

    async def run(self) -> None:
        """Main worker loop. Polls, processes concurrently, and drains on shutdown."""
        logger.info("%s started (max_messages=%d)", self.__class__.__name__, self.max_messages)

        while not self.signal_handler.signal_received:
            try:
                messages = self.input_queue_service.receive_message(max_messages=self.max_messages)

                if not messages:
                    continue

                await asyncio.gather(
                    *(self._handle_one(message, receipt_handle) for message, receipt_handle in messages),
                    return_exceptions=True,
                )
            except Exception:
                logger.exception("Unexpected error in worker poll loop")
                await asyncio.sleep(5)

        logger.info("%s received shutdown signal, exiting run loop", self.__class__.__name__)

    async def _handle_one(self, message: WorkerMessage, receipt_handle: Any) -> None:
        """Process a single message and apply completion / retry / dead-letter semantics."""
        try:
            await self.process_message(message)
        except PoisonMessageError:
            logger.exception("Poison message %s, dead-lettering", message.id)
            self.input_queue_service.deadletter_message(message, receipt_handle)
        except Exception:
            # Transient failure: reset visibility so SQS redelivers. The queue redrive
            # policy (maxReceiveCount) moves it to the DLQ after repeated failures.
            logger.exception("Transient failure processing message %s, abandoning for retry", message.id)
            self.input_queue_service.abandon_message(receipt_handle)
        else:
            self.input_queue_service.complete_message(receipt_handle)

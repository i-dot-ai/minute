"""Keeps an in-flight message's SQS lease renewed while its task runs."""

import asyncio
import contextlib
import logging
from typing import Any, Protocol

logger = logging.getLogger(__name__)


class LeaseQueue(Protocol):
    """The only queue capability the renewer needs."""

    def extend_message_lease(self, receipt_handle: Any) -> bool: ...


# Renew well under VISIBILITY_TIMEOUT_SECONDS (300s) so a single transient renewal
# failure still leaves the message invisible until the next attempt.
LEASE_RENEW_INTERVAL_SECONDS = 100


class LeaseRenewer:
    """Renew a message's visibility lease until the owner stops or loses it.

    Visibility is the crash-recovery clock: it lapses only when renewals stop — the
    worker died or the receipt is no longer valid — so a merely long-running task is
    neither redelivered nor rerun.
    """

    def __init__(
        self,
        queue_service: LeaseQueue,
        receipt_handle: Any,
        interval: float = LEASE_RENEW_INTERVAL_SECONDS,
    ):
        self.queue_service = queue_service
        self.receipt_handle = receipt_handle
        self.interval = interval
        self._task: asyncio.Task | None = None

    def start(self) -> None:
        self._task = asyncio.create_task(self._renew_forever())

    async def stop(self) -> None:
        if self._task is None:
            return
        self._task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await self._task
        self._task = None

    async def _renew_forever(self) -> None:
        while True:
            await asyncio.sleep(self.interval)
            try:
                renewed = await asyncio.to_thread(self.queue_service.extend_message_lease, self.receipt_handle)
            except Exception:
                logger.exception("Failed to extend message lease; will retry")
                continue
            if not renewed:
                # Receipt no longer valid: the message was completed or moved on.
                logger.warning("Lease renewal stopped: receipt handle is no longer valid")
                return

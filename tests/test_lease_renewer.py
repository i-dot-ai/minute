"""Tests for the per-message lease renewer (worker/lease_renewer.py).

While a task runs, its SQS visibility lease is renewed on an interval so the message
is not redelivered. Renewals stop when the worker stops the renewer, when the receipt
is no longer valid, or the owner exits.
"""

import asyncio

import pytest

from worker.lease_renewer import LeaseRenewer


class FakeQueueService:
    def __init__(self, renewed: bool = True):
        self.calls: list[object] = []
        self.renewed = renewed

    def extend_message_lease(self, receipt_handle):
        self.calls.append(receipt_handle)
        return self.renewed


@pytest.mark.asyncio(loop_scope="session")
async def test_renews_while_active():
    queue = FakeQueueService()
    renewer = LeaseRenewer(queue, "receipt", interval=0.05)

    renewer.start()
    await asyncio.sleep(0.16)
    await renewer.stop()

    assert len(queue.calls) >= 2
    assert set(queue.calls) == {"receipt"}


@pytest.mark.asyncio(loop_scope="session")
async def test_stop_cancels_renewal():
    queue = FakeQueueService()
    renewer = LeaseRenewer(queue, "receipt", interval=0.05)

    renewer.start()
    await asyncio.sleep(0.06)
    await renewer.stop()
    calls_at_stop = len(queue.calls)

    await asyncio.sleep(0.15)
    assert len(queue.calls) == calls_at_stop


@pytest.mark.asyncio(loop_scope="session")
async def test_keeps_renewing_until_owner_stops():
    queue = FakeQueueService()
    renewer = LeaseRenewer(queue, "receipt", interval=0.05)

    renewer.start()
    await asyncio.sleep(0.4)  # well past several renewal intervals
    await renewer.stop()

    assert len(queue.calls) >= 6


@pytest.mark.asyncio(loop_scope="session")
async def test_dead_receipt_stops_renewal():
    queue = FakeQueueService(renewed=False)
    renewer = LeaseRenewer(queue, "receipt", interval=0.02)

    renewer.start()
    await asyncio.sleep(0.15)
    await renewer.stop()

    assert len(queue.calls) == 1  # stopped after the first invalid receipt

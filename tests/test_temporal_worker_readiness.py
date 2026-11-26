"""The worker poll-readiness marker that gates the ECS healthcheck during rolling deploys."""

from types import SimpleNamespace

import pytest

from worker import temporal_worker


def _worker(*, running: bool) -> SimpleNamespace:
    return SimpleNamespace(is_running=running)


def test_mark_ready_writes_then_clear_removes(tmp_path, monkeypatch):
    marker = tmp_path / "worker_ready"
    monkeypatch.setattr(temporal_worker, "READINESS_FILE", marker)

    temporal_worker._mark_ready()  # noqa: SLF001
    assert marker.exists()

    temporal_worker._clear_ready()  # noqa: SLF001
    assert not marker.exists()


def test_clear_ready_is_idempotent_when_absent(tmp_path, monkeypatch):
    """Shutdown must never raise just because the marker was never written (startup failed early)."""
    monkeypatch.setattr(temporal_worker, "READINESS_FILE", tmp_path / "worker_ready")
    temporal_worker._clear_ready()  # noqa: SLF001 - missing_ok, no error


@pytest.mark.asyncio
async def test_wait_until_polling_true_once_all_running(monkeypatch):
    monkeypatch.setattr(temporal_worker, "READINESS_WAIT_SECONDS", 1)
    monkeypatch.setattr(temporal_worker, "READINESS_POLL_SECONDS", 0.01)
    workers = [_worker(running=True), _worker(running=True)]
    assert await temporal_worker._wait_until_polling(workers) is True  # noqa: SLF001


@pytest.mark.asyncio
async def test_wait_until_polling_false_if_a_worker_never_starts(monkeypatch):
    """A worker that never reports running leaves the marker absent, so ECS keeps the old task."""
    monkeypatch.setattr(temporal_worker, "READINESS_WAIT_SECONDS", 0.05)
    monkeypatch.setattr(temporal_worker, "READINESS_POLL_SECONDS", 0.01)
    workers = [_worker(running=True), _worker(running=False)]
    assert await temporal_worker._wait_until_polling(workers) is False  # noqa: SLF001

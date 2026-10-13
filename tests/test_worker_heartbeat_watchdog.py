"""Unit tests for the worker per-actor heartbeat watchdog (worker_service.py)."""

import os
import time
from pathlib import Path

import worker.worker_service as worker_service_module
from worker.worker_service import WorkerService, stale_actor_indices

TIMEOUT = 480  # mirrors HEARTBEAT_TIMEOUT; must stay a plain int for easy math


class FakeActorID:
    def __init__(self, actor_id: str):
        self._id = actor_id

    def hex(self):
        return self._id


class FakeActor:
    """Just enough of a Ray ActorHandle: the watchdog only reads _actor_id and process."""

    def __init__(self, actor_id: str):
        self._actor_id = FakeActorID(actor_id)
        self.process = FakeProcessHandle([], "idle")

    def with_process(self, calls: list[str], call: str) -> "FakeActor":
        self.process = FakeProcessHandle(calls, call)
        return self


class FakeProcessHandle:
    def __init__(self, calls: list[str], call: str):
        self.calls = calls
        self.call = call

    def remote(self):
        self.calls.append(self.call)
        return self.call


def _write_heartbeat(directory: Path, actor_id: str, mtime: float):
    path = directory / f"worker_{actor_id}.heartbeat"
    path.write_text("")
    os.utime(path, (mtime, mtime))


def test_fresh_and_missing_heartbeats_are_not_stale(tmp_path):
    actors = [FakeActor("0" * 32), FakeActor("1" * 32), FakeActor("2" * 32)]
    now = time.time()
    _write_heartbeat(tmp_path, "0" * 32, now - 10)  # fresh
    _write_heartbeat(tmp_path, "2" * 32, now - 10)  # fresh
    # actor "1" has no file yet (still starting) — must be skipped, not restarted

    assert stale_actor_indices(actors, tmp_path, now=now, timeout=TIMEOUT) == []


def test_stale_heartbeat_flags_its_actor_only(tmp_path):
    fresh_id, stale_id = "0" * 32, "1" * 32
    actors = [FakeActor(fresh_id), FakeActor(stale_id)]
    now = time.time()
    _write_heartbeat(tmp_path, fresh_id, now - 10)
    _write_heartbeat(tmp_path, stale_id, now - TIMEOUT - 1)

    assert stale_actor_indices(actors, tmp_path, now=now, timeout=TIMEOUT) == [1]


def test_boundary_age_is_not_stale(tmp_path):
    actor_id = "3" * 32
    actors = [FakeActor(actor_id)]
    now = time.time()
    _write_heartbeat(tmp_path, actor_id, now - TIMEOUT)  # exactly at the boundary

    assert stale_actor_indices(actors, tmp_path, now=now, timeout=TIMEOUT) == []


def test_stale_actor_replaced_and_healthy_actor_untouched(tmp_path, monkeypatch):
    """Orchestration: the stale actor is killed, its heartbeat file removed, and a
    replacement dispatched — without touching the healthy actor. Runs WorkerService
    without Ray (bypasses __init__) with a faked ray.kill and actor factory."""
    service = WorkerService.__new__(WorkerService)
    fresh_id, stale_id = "0" * 32, "1" * 32
    service.actors = [FakeActor(fresh_id), FakeActor(stale_id)]
    stale_actor = service.actors[1]
    service.calls = ["fresh-call", "stale-call"]
    service.num_transcription_actors = 1

    now = time.time()
    _write_heartbeat(tmp_path, fresh_id, now - 10)
    _write_heartbeat(tmp_path, stale_id, now - TIMEOUT - 1)

    killed = []

    def fake_kill(actor, no_restart=False):  # noqa: ARG001
        killed.append(actor)

    monkeypatch.setattr(worker_service_module.ray, "kill", fake_kill)
    monkeypatch.setattr(worker_service_module, "HEARTBEAT_DIR", tmp_path)

    replacement = FakeActor("f" * 32)
    replacement_calls: list[str] = []
    replacement.process = FakeProcessHandle(replacement_calls, "replacement-call")
    monkeypatch.setattr(service, "_create_actor", lambda idx: replacement)  # noqa: ARG005

    service._restart_stale_actors()  # noqa: SLF001

    assert killed == [stale_actor]
    assert service.actors[1] is replacement
    assert replacement_calls == ["replacement-call"]
    assert service.calls[0] == "fresh-call"
    # the wedged actor's heartbeat file is gone; the healthy one's remains
    assert not (tmp_path / f"worker_{stale_id}.heartbeat").exists()
    assert (tmp_path / f"worker_{fresh_id}.heartbeat").exists()


def test_timing_chain_invariants():
    """HEARTBEAT_TIMEOUT + healthcheck retries (3 x 60s) < CLAIM_STALE_AFTER <
    SQS VISIBILITY TIMEOUT. If any of these drift, recovery or duplicate-safety breaks."""
    from common.services.queue_services.sqs import VISIBILITY_TIMEOUT_SECONDS
    from common.settings import CLAIM_STALE_AFTER
    from worker.healthcheck import HEARTBEAT_TIMEOUT

    kill_bound_seconds = HEARTBEAT_TIMEOUT + 3 * 60
    claim_stale_seconds = CLAIM_STALE_AFTER.total_seconds()

    assert claim_stale_seconds > kill_bound_seconds, "a live-but-stale container could have its claim stolen"
    assert claim_stale_seconds < VISIBILITY_TIMEOUT_SECONDS, "crashed jobs would not be recovered on first redelivery"
    assert HEARTBEAT_TIMEOUT < VISIBILITY_TIMEOUT_SECONDS, "containers die long before their messages redeliver"

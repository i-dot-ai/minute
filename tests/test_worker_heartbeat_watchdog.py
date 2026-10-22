"""Unit tests for the worker per-actor heartbeat watchdog (worker_service.py)."""

import asyncio
import os
import time
from pathlib import Path
from time import monotonic

import pytest
from ray.exceptions import ActorDiedError

import worker.worker_service as worker_service_module
from worker.worker_service import WorkerService, stale_actor_indices

TIMEOUT = 60  # mirrors HEARTBEAT_TIMEOUT; must stay a plain int for easy math


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


async def _resolved_object_ref(result):
    """Stand-in for a Ray ObjectRef that completes with `result` when awaited."""
    return result


class FakeProcessHandle:
    def __init__(self, calls: list[str], call: str):
        self.calls = calls
        self.call = call

    def remote(self):
        self.calls.append(self.call)
        return _resolved_object_ref(self.call)


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


def test_fewer_workers_than_expected_is_unhealthy(tmp_path, monkeypatch):
    """Finding 9: a container configured for N actors with only some reporting must be
    unhealthy, so a silently dead-startup actor is not hidden by its healthy siblings."""
    import worker.healthcheck as healthcheck_module

    monkeypatch.setattr(healthcheck_module, "HEARTBEAT_DIR", tmp_path)
    monkeypatch.setattr(healthcheck_module, "EXPECTED_ACTORS", 2, raising=False)
    _write_heartbeat(tmp_path, "0" * 32, time.time())  # only one of two actors running

    healthy, _msg = healthcheck_module.healthcheck()

    assert healthy is False


@pytest.mark.asyncio
async def test_supported_long_running_job_is_not_treated_as_stale(tmp_path):
    """A live actor may legitimately process a job for longer than the timeout. Its
    ticker keeps the heartbeat fresh while the loop is free, so it is not flagged stale
    even though the job outlasts the (scaled-down) timeout several times over."""
    from worker.healthcheck import HeartbeatTicker

    actor_id = "4" * 32
    actor = FakeActor(actor_id)
    heartbeat = tmp_path / f"worker_{actor_id}.heartbeat"
    _write_heartbeat(tmp_path, actor_id, time.time())

    async with HeartbeatTicker(heartbeat, interval=0.05):
        await asyncio.sleep(0.3)  # job outlasts the 0.1s "timeout" below

    assert stale_actor_indices([actor], tmp_path, now=time.time(), timeout=0.1) == []


def test_stale_actor_replaced_and_healthy_actor_untouched(tmp_path, monkeypatch):
    """Orchestration: the stale actor is killed, its heartbeat file removed, and a
    replacement handle swapped in — without touching the healthy actor. The stale
    path must NOT submit process() itself: submission belongs solely to the
    failed-task loop in _check_and_restart_tasks (which fires when the killed
    actor's tracked future errors). Runs WorkerService without Ray (bypasses
    __init__) with a faked ray.kill and actor factory."""
    service = WorkerService.__new__(WorkerService)
    fresh_id, stale_id = "0" * 32, "1" * 32
    service.actors = [FakeActor(fresh_id), FakeActor(stale_id)]
    stale_actor = service.actors[1]
    service.calls = ["fresh-call", "stale-call"]

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
    monkeypatch.setattr(service, "_create_llm_actor", lambda: replacement)

    service._restart_stale_actors()

    assert killed == [stale_actor]
    assert service.actors[1] is replacement
    # no submit here — the failed-task loop owns submission, otherwise the
    # replacement would end up running two concurrent process() loops
    assert replacement_calls == []
    assert service.calls[1] == "stale-call"
    assert service.calls[0] == "fresh-call"
    # the wedged actor's heartbeat file is gone; the healthy one's remains
    assert not (tmp_path / f"worker_{stale_id}.heartbeat").exists()
    assert (tmp_path / f"worker_{fresh_id}.heartbeat").exists()


@pytest.mark.asyncio(loop_scope="session")
async def test_failed_task_restarts_on_current_actor_exactly_once():
    """The failed-task loop is the only place that re-submits process(). In the state
    a stale restart leaves behind (actor replaced, dead future still tracked), the
    dead future errors and the loop submits on the replacement actor exactly once."""
    service = WorkerService.__new__(WorkerService)
    replacement = FakeActor("f" * 32)
    replacement_calls: list[str] = []
    replacement.process = FakeProcessHandle(replacement_calls, "replacement-call")
    service.actors = [replacement]
    service.calls = ["dead-call"]
    service._last_stale_check = monotonic()  # fresh: the stale branch must not fire

    async def _died():
        raise ActorDiedError

    dead = asyncio.ensure_future(_died())
    futures = [dead]
    await service._check_and_restart_tasks(futures)
    dead.exception()  # consume so asyncio doesn't warn about an unretrieved error

    assert replacement_calls == ["replacement-call"]
    assert await futures[0] == "replacement-call"


def test_timing_chain_invariants():
    """HEARTBEAT_TIMEOUT + healthcheck grace (30s x 2) < CLAIM_STALE_AFTER <
    SQS VISIBILITY TIMEOUT, and lease renewals must land before the lease expires.
    If any of these drift, recovery or duplicate-safety breaks."""
    from common.services.queue_services.sqs import VISIBILITY_TIMEOUT_SECONDS
    from common.settings import CLAIM_STALE_AFTER
    from worker.healthcheck import HEARTBEAT_TIMEOUT
    from worker.lease_renewer import LEASE_RENEW_INTERVAL_SECONDS

    kill_bound_seconds = HEARTBEAT_TIMEOUT + 2 * 30  # mirrors worker healthcheck interval x retries
    claim_stale_seconds = CLAIM_STALE_AFTER.total_seconds()

    assert claim_stale_seconds > kill_bound_seconds, "a live-but-stale container could have its claim stolen"
    assert claim_stale_seconds < VISIBILITY_TIMEOUT_SECONDS, "crashed jobs would not be recovered on first redelivery"
    assert HEARTBEAT_TIMEOUT < VISIBILITY_TIMEOUT_SECONDS, "containers die long before their messages redeliver"
    assert LEASE_RENEW_INTERVAL_SECONDS < VISIBILITY_TIMEOUT_SECONDS, "a renewal must land before the lease expires"


@pytest.mark.asyncio(loop_scope="session")
async def test_heartbeat_ticker_stops_and_restarts_cleanly(tmp_path):
    """The ticker cancels its background task on exit and can be re-entered cleanly."""
    from worker.healthcheck import HeartbeatTicker

    path = tmp_path / "worker_deadbeef.heartbeat"
    path.touch()

    ticker = HeartbeatTicker(path, interval=0.05)
    async with ticker:
        await asyncio.sleep(0.12)
        assert ticker._task is not None
    assert ticker._task is None

    async with HeartbeatTicker(path, interval=0.05):  # re-entry must not raise
        await asyncio.sleep(0.06)


def test_restart_swap_survives_heartbeat_unlink_failure(tmp_path, monkeypatch):
    """Finding 4: a failure to remove the stale heartbeat file must not lose the
    replacement actor or retain the dead handle."""
    service = WorkerService.__new__(WorkerService)
    fresh_id, stale_id = "0" * 32, "1" * 32
    service.actors = [FakeActor(fresh_id), FakeActor(stale_id)]
    service.calls = ["fresh-call", "stale-call"]

    now = time.time()
    _write_heartbeat(tmp_path, fresh_id, now - 10)
    _write_heartbeat(tmp_path, stale_id, now - TIMEOUT - 1)

    monkeypatch.setattr(worker_service_module, "HEARTBEAT_DIR", tmp_path)
    monkeypatch.setattr(worker_service_module.ray, "kill", lambda *_a, **_k: None)

    replacement = FakeActor("f" * 32)
    monkeypatch.setattr(service, "_create_llm_actor", lambda: replacement)

    def _unlink_boom(self, *_a, **_k):  # noqa: ARG001
        msg = "cannot remove heartbeat file"
        raise OSError(msg)

    monkeypatch.setattr(Path, "unlink", _unlink_boom)

    service._restart_stale_actors()

    assert service.actors[1] is replacement


@pytest.mark.asyncio(loop_scope="session")
async def test_failed_task_exception_is_retrieved():
    """Finding 5: the failed-task loop must consume the future's exception, not just
    log the task object, so the real error is surfaced instead of leaked to the GC."""
    service = WorkerService.__new__(WorkerService)
    replacement = FakeActor("f" * 32)
    replacement_calls: list[str] = []
    replacement.process = FakeProcessHandle(replacement_calls, "replacement-call")
    service.actors = [replacement]
    service.calls = ["dead-call"]
    service._last_stale_check = monotonic()  # fresh: the stale branch must not fire

    async def _died():
        raise ActorDiedError

    dead = asyncio.ensure_future(_died())
    await service._check_and_restart_tasks([dead])

    # asyncio clears _log_traceback only when the exception has been retrieved
    assert dead._log_traceback is False


@pytest.mark.asyncio(loop_scope="session")
async def test_cancelled_future_is_restarted():
    """Finding 8: a cancelled worker future must be replaced, not left occupying a slot."""
    service = WorkerService.__new__(WorkerService)
    replacement = FakeActor("f" * 32)
    replacement_calls: list[str] = []
    replacement.process = FakeProcessHandle(replacement_calls, "replacement-call")
    service.actors = [replacement]
    service.calls = ["dead-call"]
    service._last_stale_check = monotonic()  # fresh: the stale branch must not fire

    cancelled = asyncio.ensure_future(asyncio.sleep(30))
    cancelled.cancel()
    await asyncio.sleep(0)  # let the cancellation settle

    futures = [cancelled]
    await service._check_and_restart_tasks(futures)

    assert replacement_calls == ["replacement-call"]
    assert futures[0] is not cancelled

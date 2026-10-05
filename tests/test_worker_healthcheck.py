import os
import time

from common import worker_healthcheck


def test_check_heartbeats(tmp_path, monkeypatch):
    monkeypatch.setattr(worker_healthcheck, "HEARTBEAT_DIR", tmp_path)
    heartbeat = tmp_path / "worker_1.heartbeat"
    heartbeat.touch()
    assert worker_healthcheck.check_heartbeats("worker_*.heartbeat", 90) == (True, "HEALTHY: 1 active workers")

    os.utime(heartbeat, (time.time() - 91, time.time() - 91))
    assert worker_healthcheck.check_heartbeats("worker_*.heartbeat", 90) == (
        False,
        "UNHEALTHY: Stale workers ['worker_1']",
    )

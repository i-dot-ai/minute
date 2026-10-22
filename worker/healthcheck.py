import asyncio
import contextlib
import logging
import sys
import time
from os import getenv
from pathlib import Path

logger = logging.getLogger()


HEARTBEAT_DIR = Path(getenv("HEARTBEAT_DIR", "/healthcheck"))
# A heartbeat untouched this long means the receive loop is wedged (a live task keeps it
# fresh via HeartbeatTicker, and lease renewal keeps a long task off the redelivery path).
# With 30s healthcheck x 2 retries the container is replaced ~120s after its last touch,
# the in-container watchdog fires sooner (~75s). Must stay under CLAIM_STALE_AFTER and
# VISIBILITY_TIMEOUT so a wedged actor is replaced before its job is reclaimed.
HEARTBEAT_TIMEOUT = 60

# How often an actor re-touches its heartbeat while its receive loop is alive. A few
# times under HEARTBEAT_TIMEOUT so brief loop pauses are tolerated but a wedge is caught.
HEARTBEAT_TOUCH_INTERVAL = 15

# Number of actors this container should run, reusing the same env the worker reads.
# Zero means "not configured" (e.g. host-run tests) and disables the count check; when
# set, a container with fewer reporting actors is unhealthy, so an actor that dies
# during startup is not hidden by its healthy siblings.
EXPECTED_ACTORS = int(getenv("MAX_LLM_PROCESSES", "0"))


class HeartbeatTicker:
    """Keeps a heartbeat file fresh for as long as its owning loop is running.

    A worker actor must not go stale just because a single task is awaiting an
    external call for longer than HEARTBEAT_TIMEOUT. Ticking from a side task touches
    the file while the loop is free; a genuinely blocked event loop starves the ticker
    too, so a wedged actor still goes stale and is still detected.
    """

    def __init__(self, path: Path, interval: float = HEARTBEAT_TOUCH_INTERVAL):
        self.path = path
        self.interval = interval
        self._task: asyncio.Task | None = None

    async def _tick_forever(self) -> None:
        while True:
            await asyncio.sleep(self.interval)
            self.path.touch()

    async def __aenter__(self) -> "HeartbeatTicker":
        self._task = asyncio.create_task(self._tick_forever())
        return self

    async def __aexit__(self, *_exc: object) -> None:
        if self._task is None:
            return
        self._task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await self._task
        self._task = None


def ensure_heartbeat_dir() -> None:
    """Create the heartbeat directory if it does not already exist.

    Done lazily rather than at import time so that importing this module has no
    filesystem side effects (e.g. when running tests outside the worker container).
    """
    HEARTBEAT_DIR.mkdir(parents=True, exist_ok=True)


def healthcheck() -> tuple[bool, str]:
    current_time = time.time()
    heartbeat_files = list(HEARTBEAT_DIR.glob("worker_*.heartbeat"))
    if not heartbeat_files:
        return False, "UNHEALTHY: No workers found."

    if EXPECTED_ACTORS and len(heartbeat_files) < EXPECTED_ACTORS:
        return False, f"UNHEALTHY: {len(heartbeat_files)} of {EXPECTED_ACTORS} workers reporting"

    stale_workers = []
    for hb_file in heartbeat_files:
        last_heartbeat = hb_file.stat().st_mtime
        age = current_time - last_heartbeat

        if age > HEARTBEAT_TIMEOUT:
            stale_workers.append(hb_file.stem)

    if stale_workers:
        return False, f"UNHEALTHY: State workers {stale_workers}"

    return True, f"HEALTHY: {len(heartbeat_files)} active workers"


if __name__ == "__main__":
    healthy, msg = healthcheck()
    if healthy:
        logger.info(msg)
    else:
        logger.warning(msg)
        sys.exit(msg)

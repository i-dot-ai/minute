import logging
import sys
import time
from os import getenv
from pathlib import Path

logger = logging.getLogger()


HEARTBEAT_DIR = Path(getenv("HEARTBEAT_DIR", "/healthcheck"))
HEARTBEAT_TIMEOUT = 1200  # 20 minutes


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

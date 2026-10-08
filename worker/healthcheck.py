import logging
import sys
import time
from os import getenv
from pathlib import Path

logger = logging.getLogger()

HEARTBEAT_DIR = Path(getenv("HEARTBEAT_DIR", "/healthcheck"))
HEARTBEAT_TIMEOUT = 1200  # 20 minutes


def ensure_heartbeat_dir() -> None:
    HEARTBEAT_DIR.mkdir(parents=True, exist_ok=True)


def healthcheck() -> tuple[bool, str]:
    heartbeat_files = list(HEARTBEAT_DIR.glob("worker_*.heartbeat"))
    if not heartbeat_files:
        return False, "UNHEALTHY: No workers found."

    current_time = time.time()
    stale_workers = [
        heartbeat.stem for heartbeat in heartbeat_files if current_time - heartbeat.stat().st_mtime > HEARTBEAT_TIMEOUT
    ]
    if stale_workers:
        return False, f"UNHEALTHY: Stale workers {stale_workers}"

    return True, f"HEALTHY: {len(heartbeat_files)} active workers"


if __name__ == "__main__":
    healthy, msg = healthcheck()
    if healthy:
        logger.info(msg)
    else:
        logger.warning(msg)
        sys.exit(msg)

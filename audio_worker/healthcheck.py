import sys
import time
from os import getenv
from pathlib import Path

from common.settings import get_structured_logger

slogger = get_structured_logger()


HEARTBEAT_DIR = Path(getenv("HEARTBEAT_DIR", "/healthcheck"))
HEARTBEAT_TIMEOUT = 90


def healthcheck() -> tuple[bool, str]:
    current_time = time.time()
    heartbeat_files = list(HEARTBEAT_DIR.glob("audio_worker_*.heartbeat"))
    if not heartbeat_files:
        return False, "UNHEALTHY: No workers found."

    stale_workers = []
    for hb_file in heartbeat_files:
        last_heartbeat = hb_file.stat().st_mtime
        age = current_time - last_heartbeat

        if age > HEARTBEAT_TIMEOUT:
            stale_workers.append(hb_file.stem)

    if stale_workers:
        return False, f"UNHEALTHY: Stale workers {stale_workers}"

    return True, f"HEALTHY: {len(heartbeat_files)} active workers"


if __name__ == "__main__":
    healthy, msg = healthcheck()
    if healthy:
        slogger.info("Healthy: {status}", status=msg)
    else:
        slogger.warning("Unhealthy: {status}", status=msg)
        sys.exit(msg)

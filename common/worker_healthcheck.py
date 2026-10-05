import time
from os import getenv
from pathlib import Path

HEARTBEAT_DIR = Path(getenv("HEARTBEAT_DIR", "/healthcheck"))


def ensure_heartbeat_dir() -> None:
    HEARTBEAT_DIR.mkdir(parents=True, exist_ok=True)


def check_heartbeats(pattern: str, timeout: float) -> tuple[bool, str]:
    heartbeat_files = list(HEARTBEAT_DIR.glob(pattern))
    if not heartbeat_files:
        return False, "UNHEALTHY: No workers found."

    current_time = time.time()
    stale_workers = [path.stem for path in heartbeat_files if current_time - path.stat().st_mtime > timeout]
    if stale_workers:
        return False, f"UNHEALTHY: Stale workers {stale_workers}"

    return True, f"HEALTHY: {len(heartbeat_files)} active workers"

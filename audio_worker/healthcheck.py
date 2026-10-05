import sys

from common.settings import get_structured_logger
from common.worker_healthcheck import check_heartbeats

slogger = get_structured_logger()

HEARTBEAT_TIMEOUT = 90


def healthcheck() -> tuple[bool, str]:
    return check_heartbeats("audio_worker_*.heartbeat", HEARTBEAT_TIMEOUT)


if __name__ == "__main__":
    healthy, msg = healthcheck()
    if healthy:
        slogger.info("Healthy: {status}", status=msg)
    else:
        slogger.warning("Unhealthy: {status}", status=msg)
        sys.exit(msg)

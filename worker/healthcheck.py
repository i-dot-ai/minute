import logging
import sys

from common.worker_healthcheck import check_heartbeats

logger = logging.getLogger()

HEARTBEAT_TIMEOUT = 1200  # 20 minutes


def healthcheck() -> tuple[bool, str]:
    return check_heartbeats("worker_*.heartbeat", HEARTBEAT_TIMEOUT)


if __name__ == "__main__":
    healthy, msg = healthcheck()
    if healthy:
        logger.info(msg)
    else:
        logger.warning(msg)
        sys.exit(msg)

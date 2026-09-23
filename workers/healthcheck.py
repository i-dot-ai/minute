import logging
import sys

logger = logging.getLogger()


def healthcheck() -> tuple[bool, str]:
    """Simple healthcheck - worker process is alive."""
    return True, "Worker process healthy"


if __name__ == "__main__":
    healthy, msg = healthcheck()
    if healthy:
        logger.info(msg)
    else:
        logger.warning(msg)
        sys.exit(msg)

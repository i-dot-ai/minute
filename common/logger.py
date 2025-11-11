from functools import lru_cache
import logging
from i_dot_ai_utilities.logging.structured_logger import StructuredLogger

from common.settings import get_settings


def setup_logger():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

def setup_structured_logger(level: str | None = None) -> StructuredLogger:
    return StructuredLogger(
        level=level or "info",
        options={
            "execution_environment": get_settings().EXECUTION_ENVIRONMENT,
            "log_format": get_settings().LOGGING_FORMAT,
        },
    )

@lru_cache
def get_structured_logger() -> StructuredLogger:
    return setup_structured_logger(level=get_settings().LOG_LEVEL or "info")

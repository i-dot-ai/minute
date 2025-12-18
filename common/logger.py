import logging

from i_dot_ai_utilities.logging.structured_logger import StructuredLogger
from i_dot_ai_utilities.logging.types.enrichment_types import ExecutionEnvironmentType
from i_dot_ai_utilities.logging.types.log_output_format import LogOutputFormat


def setup_logger():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


def setup_structured_logger(
    level: str, execution_environment: ExecutionEnvironmentType, logging_format: LogOutputFormat
) -> StructuredLogger:
    return StructuredLogger(
        level=level or "info",
        options={
            "execution_environment": execution_environment,
            "log_format": logging_format,
        },
    )

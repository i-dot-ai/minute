import logging

from i_dot_ai_utilities.logging.structured_logger import StructuredLogger
from i_dot_ai_utilities.logging.types.enrichment_types import ExecutionEnvironmentType
from i_dot_ai_utilities.logging.types.log_output_format import LogOutputFormat


class _SearchQueryFilter(logging.Filter):
    def filter(self, record):
        args = record.args
        # Uvicorn passes (client, method, path, HTTP version, status) as formatting arguments.
        if isinstance(args, tuple) and len(args) == 5 and str(args[2]).startswith("/transcriptions/search?"):  # noqa: PLR2004
            record.args = (*args[:2], args[2].partition("?")[0], *args[3:])
        return True


def setup_logger():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    logging.getLogger("uvicorn.access").addFilter(_SearchQueryFilter())


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

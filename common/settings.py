import logging
from functools import lru_cache

import dotenv
from i_dot_ai_utilities.logging.structured_logger import StructuredLogger
from i_dot_ai_utilities.logging.types.enrichment_types import ExecutionEnvironmentType
from i_dot_ai_utilities.logging.types.log_output_format import LogOutputFormat
from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from common.logger import setup_logger, setup_structured_logger

setup_logger()
logger = logging.getLogger(__name__)

DOT_ENV_PATH = ".env"

dotenv_detected = dotenv.load_dotenv(dotenv_path=DOT_ENV_PATH)
if dotenv_detected:
    logger.debug("A .env file was detected and loaded. Values from it will override environment variables")
else:
    logger.debug("No .env file was detected. Using environment variables as is")


class Settings(BaseSettings):
    POSTGRES_HOST: str = Field(description="PostgreSQL database host")
    POSTGRES_PORT: int = Field(description="PostgreSQL database port")
    POSTGRES_DB: str = Field(description="PostgreSQL database name")
    POSTGRES_USER: str = Field(description="PostgreSQL database user")
    POSTGRES_PASSWORD: str = Field(description="PostgreSQL database password")

    APP_URL: str = Field(description="used for CORS origin validation")

    # if using AWS
    AWS_ACCOUNT_ID: str | None = Field(description="AWS account ID", default=None)
    AWS_REGION: str | None = Field(description="AWS region", default=None)

    # if using i.AI Auth API
    REPO: str = Field(description="The name of the GitHub repository")
    AUTH_API_URL: str = Field(description="The hostname of the Auth API")
    AUTH_API_REQUEST_TIMEOUT: int | None = Field(
        description="The timeout in seconds to wait for auth response", default=None
    )

    ENVIRONMENT: str = "local"
    SENTRY_DSN: str | None = Field(description="Sentry DSN if using Sentry for telemetry", default=None)

    # Structured logger setup. These are derived from ENVIRONMENT at runtime (see the
    # validator below) rather than as class-level expressions, which would only ever see
    # the "local" default and force TEXT/LOCAL regardless of the actual environment.
    EXECUTION_ENVIRONMENT: ExecutionEnvironmentType = ExecutionEnvironmentType.LOCAL
    LOGGING_FORMAT: LogOutputFormat = LogOutputFormat.TEXT
    LOG_LEVEL: str = Field(description="The level at which to emit structured logs", default="info")

    @model_validator(mode="after")
    def _derive_logging_from_environment(self) -> "Settings":
        is_local = self.ENVIRONMENT.lower() == "local"
        self.EXECUTION_ENVIRONMENT = ExecutionEnvironmentType.LOCAL if is_local else ExecutionEnvironmentType.FARGATE
        self.LOGGING_FORMAT = LogOutputFormat.TEXT if is_local else LogOutputFormat.JSON
        return self

    WORKER_QUEUE_NAME: str = Field(description="SQS queue the worker consumes jobs from")
    WORKER_DEADLETTER_QUEUE_NAME: str = Field(description="SQS dead-letter queue for the worker queue")

    AZURE_SPEECH_KEY: str = Field(description="Azure STT speech key for API")
    AZURE_SPEECH_REGION: str = Field(description="Region for Azure STT")
    # optional extra Azure STT regions, tried in order when a region returns 429 or 5xx
    AZURE_SPEECH_FALLBACK_1_KEY: str | None = Field(description="Azure STT speech key for fallback 1", default=None)
    AZURE_SPEECH_FALLBACK_1_REGION: str | None = Field(description="Region for Azure STT fallback 1", default=None)
    AZURE_SPEECH_FALLBACK_2_KEY: str | None = Field(description="Azure STT speech key for fallback 2", default=None)
    AZURE_SPEECH_FALLBACK_2_REGION: str | None = Field(description="Region for Azure STT fallback 2", default=None)

    MAX_CONCURRENT_TRANSCRIPTIONS: int = Field(
        description="Concurrent transcription-phase jobs (audio download/convert + STT call) per worker task",
        default=2,
    )
    MAX_CONCURRENT_LLM: int = Field(
        description="Concurrent LLM-phase jobs (speakers, title, minute generation, edits) per worker task",
        default=4,
    )
    JOB_VISIBILITY_TIMEOUT_SECS: int = Field(
        description="SQS visibility timeout applied when a message is received/extended; the consumer heartbeat "
        "re-extends it while a job is alive",
        default=300,
    )
    JOB_HEARTBEAT_INTERVAL_SECS: int = Field(
        description="How often the consumer extends a job's SQS visibility while it is processing",
        default=120,
    )
    JOB_STALE_SECONDS: int = Field(
        description="A claim whose claimed_at is older than this is stealable on redelivery (worker died)",
        default=600,
    )

    # if using Azure OpenAI
    AZURE_DEPLOYMENT: str | None = Field(description="Azure deployment for openAI", default=None)
    AZURE_OPENAI_API_KEY: str | None = Field(description="Azure API key for openAI", default=None)
    AZURE_OPENAI_ENDPOINT: str | None = Field(description="Azure OpenAI service endpoint URL", default=None)
    AZURE_OPENAI_API_VERSION: str | None = Field(description="Azure OpenAI API version", default=None)

    # GOOGLE_APPLICATION_CREDENTIALS and GOOGLE_CLOUD_PROJECT are read directly by the Google SDK.
    GOOGLE_CLOUD_LOCATION: str | None = Field(description="Google Cloud region/location", default=None)

    # if using MiniStack for development (recommended)
    USE_MINISTACK: bool = Field(description="Use MiniStack for local AWS services emulation in dev", default=True)
    MINISTACK_URL: str = Field(
        description="MiniStack service URL for local AWS services emulation", default="http://localhost:4566"
    )

    FAST_LLM_PROVIDER: str = Field(
        description="Fast LLM provider to use. Currently 'openai' or 'gemini' are supported. Note that this should be "
        "used for low complexity LLM tasks, like AI edits",
        default="gemini",
    )
    FAST_LLM_MODEL_NAME: str = Field(
        description="Fast LLM model name to use. Note that this should be used for low complexity LLM tasks",
        default="gemini-3.5-flash",
    )
    BEST_LLM_PROVIDER: str = Field(
        description="Best LLM provider to use. Currently 'openai' or 'gemini' are supported. Note that this should be "
        "used for higher complexity LLM tasks, like initial minute generation.",
        default="gemini",
    )
    BEST_LLM_MODEL_NAME: str = Field(
        description="Best LLM model name to use. Note that this should be used for higher complexity LLM tasks, like "
        "initial minute generation.",
        default="gemini-3.5-flash",
    )

    STORAGE_SERVICE_NAME: str = Field(
        description="Storage service type to use for file uploads. Currently supported are: s3, local",
        default="s3",
    )
    # if using s3
    DATA_S3_BUCKET: str | None = Field(description="S3 bucket name for data storage", default=None)

    QUEUE_SERVICE_NAME: str = Field(
        description="Queue service type to communicate with worker. Currently supported: sqs",
        default="sqs",
    )

    BETA_TEMPLATE_NAMES: list[str] = Field(
        description="List of template names hidden from users",
        default_factory=list,
    )

    # if using posthog
    POSTHOG_API_KEY: str | None = Field(description="PostHog API key for analytics", default=None)
    POSTHOG_HOST: str = Field(description="PostHog service host URL", default="https://eu.i.posthog.com")

    MIN_WORD_COUNT_FOR_SUMMARY: int = Field(
        default=200, description="Transcript must have at least this many words to be passed to summary stage"
    )
    MIN_WORD_COUNT_FOR_FULL_SUMMARY: int = Field(
        default=199,
        description=(
            "Transcript must have at least this many words to be passed to complex summary stage. "
            "Note, this is disabled by default as is lower than the MIN_WORD_COUNT_FOR_SUMMARY"
        ),
    )

    SEARCH_SIMILARITY_THRESHOLD: float = Field(
        default=0.3,
        description="Minimum pg_trgm similarity for a title to count as a fuzzy search match",
    )

    LOCAL_STORAGE_PATH: str = Field(
        default="/tmp",  # noqa: S108
        description="The folder where the data directory is mounted for the local storage service.",
    )

    # use a dotenv file for local development
    if dotenv_detected:
        model_config = SettingsConfigDict(env_file=DOT_ENV_PATH, extra="ignore")


def get_settings():
    return Settings()  # type: ignore  # noqa: PGH003


@lru_cache
def get_structured_logger() -> StructuredLogger:
    return setup_structured_logger(
        level=get_settings().LOG_LEVEL or "info",
        execution_environment=get_settings().EXECUTION_ENVIRONMENT,
        logging_format=get_settings().LOGGING_FORMAT,
    )

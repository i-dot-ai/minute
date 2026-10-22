import logging
from datetime import timedelta
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

# Worker job claims older than this are considered abandoned and safe to reclaim.
# Coupling: a worker container is replaced ~120s after its last heartbeat
# (HEARTBEAT_TIMEOUT 60s + healthcheck 30s x 2 retries), so 3 min claims can only be
# a crashed claimant, and 5 min SQS visibility guarantees every stale claim is
# reclaimable on its first redelivery. Lease renewal (worker/lease_renewer.py) keeps a
# long-running task's message invisible, so task duration no longer affects this chain.
CLAIM_STALE_AFTER = timedelta(minutes=3)

dotenv_detected = dotenv.load_dotenv(dotenv_path=DOT_ENV_PATH)
if dotenv_detected:
    logger.info("A .env file was detected and loaded. Values from it will override environment variables")
else:
    logger.info("No .env file was detected. Using environment variables as is")


class Settings(BaseSettings):
    POSTGRES_HOST: str = Field(description="PostgreSQL database host")
    POSTGRES_PORT: int = Field(description="PostgreSQL database port")
    POSTGRES_DB: str = Field(description="PostgreSQL database name")
    POSTGRES_USER: str = Field(description="PostgreSQL database user")
    POSTGRES_PASSWORD: str = Field(description="PostgreSQL database password")

    APP_URL: str = Field(description="used for CORS origin validation")

    # if using AWS
    AWS_DEFAULT_REGION: str | None = Field(description="AWS region", default=None)
    # Local dev points these at MiniStack; deployed environments leave them unset (no
    # endpoint, credentials from the ECS task role) so boto3 falls back to its chain.
    AWS_ACCESS_KEY_ID: str | None = Field(description="AWS access key id", default=None)
    AWS_SECRET_ACCESS_KEY: str | None = Field(description="AWS secret access key", default=None)
    AWS_ENDPOINT_URL: str | None = Field(description="Custom AWS endpoint URL (MiniStack locally)", default=None)
    AWS_S3_BUCKET: str = Field()

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

    LLM_QUEUE_NAME: str = Field(description="SQS LLM queue name")
    LLM_DEADLETTER_QUEUE_NAME: str = Field(description="SQS LLM dead-letter queue name")

    AZURE_SPEECH_KEY: str = Field(description="Azure STT speech key for API")
    AZURE_SPEECH_REGION: str = Field(description="Region for Azure STT")
    # optional extra Azure STT regions, tried in order when a region returns 429 or 5xx
    AZURE_SPEECH_FALLBACK_1_KEY: str | None = Field(description="Azure STT speech key for fallback 1", default=None)
    AZURE_SPEECH_FALLBACK_1_REGION: str | None = Field(description="Region for Azure STT fallback 1", default=None)
    AZURE_SPEECH_FALLBACK_2_KEY: str | None = Field(description="Azure STT speech key for fallback 2", default=None)
    AZURE_SPEECH_FALLBACK_2_REGION: str | None = Field(description="Region for Azure STT fallback 2", default=None)

    MAX_LLM_PROCESSES: int = Field(
        description="Ray LLM actors per node; also the Temporal 'llm' queue cap (concurrent speaker/title/summary "
        "steps) per temporal-worker process",
        default=1,
    )

    # if using Azure OpenAI
    AZURE_DEPLOYMENT: str | None = Field(description="Azure deployment for openAI", default=None)
    AZURE_OPENAI_API_KEY: str | None = Field(description="Azure API key for openAI", default=None)
    AZURE_OPENAI_ENDPOINT: str | None = Field(description="Azure OpenAI service endpoint URL", default=None)
    AZURE_OPENAI_API_VERSION: str | None = Field(description="Azure OpenAI API version", default=None)

    # GOOGLE_APPLICATION_CREDENTIALS and GOOGLE_CLOUD_PROJECT are read directly by the Google SDK.
    GOOGLE_CLOUD_LOCATION: str | None = Field(description="Google Cloud region/location", default=None)

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

    QUEUE_SERVICE_NAME: str = Field(
        description="Queue service type to communicate with worker. Currently supported: sqs",
        default="sqs",
    )

    TEMPORAL_ADDRESS: str = Field(description="Temporal frontend gRPC address", default="localhost:7233")
    TEMPORAL_NAMESPACE: str = Field(description="Temporal namespace", default="default")
    STT_MAX_CONCURRENCY: int = Field(
        description="Max concurrent Azure STT calls per Temporal STT worker. The cluster-wide cap is this times "
        "the number of worker processes polling the 'stt' task queue.",
        default=4,
    )

    # if running the worker inside a docker container (use "0.0.0.0" )
    RAY_DASHBOARD_HOST: str = Field(description="Ray dashboard host IP address", default="127.0.0.1")

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

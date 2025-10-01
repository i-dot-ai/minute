import logging
from functools import lru_cache

import dotenv
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from common.logger import setup_logger

setup_logger()
logger = logging.getLogger(__name__)

DOT_ENV_PATH = ".env"

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
    AWS_ACCOUNT_ID: str | None = Field(description="AWS account ID", default=None)
    AWS_REGION: str | None = Field(description="AWS region", default=None)

    ENVIRONMENT: str = Field(
        description='use "local" for local development, or dev,preprod or prod as appropriate', default="local"
    )
    SENTRY_DSN: str | None = Field(description="Sentry DSN if using Sentry for telemetry", default=None)

    QUEUE_NAME: str = Field(description="queue name to use for SQS/Azure Service Bus queues")
    DEADLETTER_QUEUE_NAME: str = Field(
        description="deadletter queue name to use for SQS. Ignored if using Azure Service Bus "
    )

    AZURE_SPEECH_KEY: str = Field(description="Azure STT speech key for API")
    AZURE_SPEECH_REGION: str = Field(description="Region for Azure STT")

    MAX_TRANSCRIPTION_PROCESSES: int = Field(description="the number of transcription workers per node", default=1)
    MAX_LLM_PROCESSES: int = Field(description="the number of LLM workers per node", default=1)

    # if using Azure OpenAI
    AZURE_DEPLOYMENT: str | None = Field(description="Azure deployment for openAI", default=None)
    AZURE_OPENAI_API_KEY: str | None = Field(description="Azure API key for openAI", default=None)
    AZURE_OPENAI_ENDPOINT: str | None = Field(description="Azure OpenAI service endpoint URL", default=None)
    AZURE_OPENAI_API_VERSION: str | None = Field(description="Azure OpenAI API version", default=None)

    # if using Gemini
    GOOGLE_APPLICATION_CREDENTIALS: str | None = Field(
        description="Path to Google Cloud service account credentials JSON file", default=None
    )
    GOOGLE_CLOUD_PROJECT: str | None = Field(description="Google Cloud project ID", default=None)
    GOOGLE_CLOUD_LOCATION: str | None = Field(description="Google Cloud region/location", default=None)

    # if using LOCALSTACK for development (recommended)
    USE_LOCALSTACK: bool = Field(description="Use LocalStack for local AWS services emulation in dev", default=True)
    LOCALSTACK_URL: str = Field(
        description="LocalStack service URL for local AWS services emulation", default="http://localhost:4566"
    )

    TRANSCRIPTION_SERVICES: list[str] = Field(
        description="List of service names to use for transcription. See backend/services/transcription_services",
        default_factory=list,
    )

    FAST_LLM_PROVIDER: str = Field(
        description="Fast LLM provider to use. Currently 'openai' or 'gemini' are supported. Note that this should be "
        "used for low complexity LLM tasks, like AI edits",
        default="gemini",
    )
    FAST_LLM_MODEL_NAME: str = Field(
        description="Fast LLM model name to use. Note that this should be used for low complexity LLM tasks",
        default="gemini-2.5-flash-lite",
    )
    BEST_LLM_PROVIDER: str = Field(
        description="Best LLM provider to use. Currently 'openai' or 'gemini' are supported. Note that this should be "
        "used for higher complexity LLM tasks, like initial minute generation.",
        default="gemini",
    )
    BEST_LLM_MODEL_NAME: str = Field(
        description="Best LLM model name to use. Note that this should be used for higher complexity LLM tasks, like "
        "initial minute generation.",
        default="gemini-2.5-flash",
    )

    STORAGE_SERVICE_NAME: str = Field(
        description="Storage service type to use for file uploads. Currently supported are: s3, azure-blob",
        default="s3",
    )
    # if using s3
    DATA_S3_BUCKET: str | None = Field(description="S3 bucket name for data storage", default=None)
    # if using Azure blob
    AZURE_BLOB_CONNECTION_STRING: str | None = Field(description="Azure Blob Storage connection string", default=None)
    AZURE_UPLOADS_CONTAINER_NAME: str | None = Field(
        description="Azure container name for uploaded files", default=None
    )
    # if using azure_stt_batch
    AZURE_TRANSCRIPTION_CONTAINER_NAME: str | None = Field(
        description="Azure container name for transcription result files. Note that Azure Batch transcription requires "
        "this.",
        default=None,
    )

    QUEUE_SERVICE_NAME: str = Field(
        description="Queue service type to communicate with worker. Currently supported are: sqs, azure-service-bus",
        default="sqs",
    )
    # if using azure-service-bus
    AZURE_SB_CONNECTION_STRING: str | None = Field(description="Azure service bus connection string", default=None)

    # if running the worker inside a docker container (use "0.0.0.0" )
    RAY_DASHBOARD_HOST: str = Field(description="Ray dashboard host IP address", default="127.0.0.1")

    BETA_TEMPLATE_NAMES: list[str] = Field(
        description="List of template names available in beta. These are currently made available via a Posthog feature"
        " flag",
        default_factory=list,
    )

    # if using posthog
    POSTHOG_API_KEY: str | None = Field(description="PostHog API key for analytics", default=None)
    POSTHOG_HOST: str = Field(description="PostHog service host URL", default="https://eu.i.posthog.com")

    HALLUCINATION_CHECK: bool = Field(
        description="Should the LLM check for hallucinations? Note that the results of"
        " this are currently not surfaced in the UI",
        default=False,
    )

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

    # use a dotenv file for local development
    if dotenv_detected:
        model_config = SettingsConfigDict(env_file=DOT_ENV_PATH, extra="ignore")


@lru_cache
def get_settings():
    return Settings()  # type: ignore  # noqa: PGH003

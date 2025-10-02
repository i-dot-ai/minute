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
    POSTGRES_HOST: str = Field(description="PostgreSQL database host", json_schema_extra={"category": "database"})
    POSTGRES_PORT: int = Field(description="PostgreSQL database port", json_schema_extra={"category": "database"})
    POSTGRES_DB: str = Field(description="PostgreSQL database name", json_schema_extra={"category": "database"})
    POSTGRES_USER: str = Field(description="PostgreSQL database user", json_schema_extra={"category": "database"})
    POSTGRES_PASSWORD: str = Field(
        description="PostgreSQL database password", json_schema_extra={"category": "database"}
    )

    APP_URL: str = Field(description="used for CORS origin validation", json_schema_extra={"category": "Application"})
    ENVIRONMENT: str = Field(
        description='use "local" for local development, or dev,preprod or prod as appropriate',
        default="local",
        json_schema_extra={"category": "Application"},
    )
    SENTRY_DSN: str | None = Field(
        description="Sentry DSN if using Sentry for telemetry",
        default=None,
        json_schema_extra={"category": "Application"},
    )

    # if using AWS
    AWS_ACCOUNT_ID: str | None = Field(
        description="AWS account ID", default=None, json_schema_extra={"category": "AWS"}
    )
    AWS_REGION: str | None = Field(description="AWS region", default=None, json_schema_extra={"category": "AWS"})

    QUEUE_NAME: str = Field(
        description="queue name to use for SQS/Azure Service Bus queues",
        json_schema_extra={"category": "Queue services"},
    )
    DEADLETTER_QUEUE_NAME: str = Field(
        description="deadletter queue name to use for SQS. Ignored if using Azure Service Bus.",
        json_schema_extra={"category": "Queue services"},
    )

    QUEUE_SERVICE_NAME: str = Field(
        description="Queue service type to communicate with worker. Currently supported are: sqs, azure-service-bus",
        default="sqs",
        json_schema_extra={"category": "Queue services"},
    )
    AZURE_SPEECH_KEY: str = Field(
        description="Azure STT speech key for API", json_schema_extra={"category": "Azure speech"}
    )
    AZURE_SPEECH_REGION: str = Field(description="Region for Azure STT", json_schema_extra={"category": "Azure speech"})

    MAX_TRANSCRIPTION_PROCESSES: int = Field(
        description="the number of transcription workers per node",
        default=1,
        json_schema_extra={"category": "Worker Configuration"},
    )
    MAX_LLM_PROCESSES: int = Field(
        description="the number of LLM workers per node",
        default=1,
        json_schema_extra={"category": "Worker Configuration"},
    )

    # if using Azure OpenAI
    AZURE_DEPLOYMENT: str | None = Field(
        description="Azure deployment for openAI", default=None, json_schema_extra={"category": "Azure OpenAI"}
    )
    AZURE_OPENAI_API_KEY: str | None = Field(
        description="Azure API key for openAI", default=None, json_schema_extra={"category": "Azure OpenAI"}
    )
    AZURE_OPENAI_ENDPOINT: str | None = Field(
        description="Azure OpenAI service endpoint URL", default=None, json_schema_extra={"category": "Azure OpenAI"}
    )
    AZURE_OPENAI_API_VERSION: str | None = Field(
        description="Azure OpenAI API version", default=None, json_schema_extra={"category": "Azure OpenAI"}
    )

    # if using Gemini
    GOOGLE_APPLICATION_CREDENTIALS: str | None = Field(
        description="Path to Google Cloud service account credentials JSON file",
        default=None,
        json_schema_extra={"category": "Google Cloud"},
    )
    GOOGLE_CLOUD_PROJECT: str | None = Field(
        description="Google Cloud project ID", default=None, json_schema_extra={"category": "Google Cloud"}
    )
    GOOGLE_CLOUD_LOCATION: str | None = Field(
        description="Google Cloud region/location", default=None, json_schema_extra={"category": "Google Cloud"}
    )

    # if using LOCALSTACK for development (recommended)
    USE_LOCALSTACK: bool = Field(
        description="Use LocalStack for local AWS services emulation in dev",
        default=True,
        json_schema_extra={"category": "LocalStack"},
    )
    LOCALSTACK_URL: str = Field(
        description="LocalStack service URL for local AWS services emulation",
        default="http://localhost:4566",
        json_schema_extra={"category": "LocalStack"},
    )

    TRANSCRIPTION_SERVICES: list[str] = Field(
        description="List of service names to use for transcription. See backend/services/transcription_services",
        default_factory=lambda: ["azure_stt_synchronous", "azure_stt_batch"],
        json_schema_extra={"category": "Transcription"},
    )

    FAST_LLM_PROVIDER: str = Field(
        description="Fast LLM provider to use. Currently 'openai' or 'gemini' are supported. Note that this should be "
        "used for low complexity LLM tasks, like AI edits",
        default="gemini",
        json_schema_extra={"category": "LLM Configuration"},
    )
    FAST_LLM_MODEL_NAME: str = Field(
        description="Fast LLM model name to use. Note that this should be used for low complexity LLM tasks",
        default="gemini-2.5-flash-lite",
        json_schema_extra={"category": "LLM Configuration"},
    )
    BEST_LLM_PROVIDER: str = Field(
        description="Best LLM provider to use. Currently 'openai' or 'gemini' are supported. Note that this should be "
        "used for higher complexity LLM tasks, like initial minute generation.",
        default="gemini",
        json_schema_extra={"category": "LLM Configuration"},
    )
    BEST_LLM_MODEL_NAME: str = Field(
        description="Best LLM model name to use. Note that this should be used for higher complexity LLM tasks, like "
        "initial minute generation.",
        default="gemini-2.5-flash",
        json_schema_extra={"category": "LLM Configuration"},
    )

    STORAGE_SERVICE_NAME: str = Field(
        description="Storage service type to use for file uploads. Currently supported are: s3, azure-blob",
        default="s3",
        json_schema_extra={"category": "Storage"},
    )
    # if using s3
    DATA_S3_BUCKET: str | None = Field(
        description="S3 bucket name for data storage", default=None, json_schema_extra={"category": "Storage"}
    )
    # if using Azure blob
    AZURE_BLOB_CONNECTION_STRING: str | None = Field(
        description="Azure Blob Storage connection string", default=None, json_schema_extra={"category": "Storage"}
    )
    AZURE_UPLOADS_CONTAINER_NAME: str | None = Field(
        description="Azure container name for uploaded files", default=None, json_schema_extra={"category": "Storage"}
    )
    # if using azure_stt_batch
    AZURE_TRANSCRIPTION_CONTAINER_NAME: str | None = Field(
        description="Azure container name for transcription result files. Note that Azure Batch transcription requires "
        "this.",
        default=None,
        json_schema_extra={"category": "Storage"},
    )

    # if using azure-service-bus
    AZURE_SB_CONNECTION_STRING: str | None = Field(
        description="Azure service bus connection string",
        default=None,
        json_schema_extra={"category": "Queue Services"},
    )

    RAY_DASHBOARD_HOST: str = Field(
        description="Ray dashboard host IP address. Use '0.0.0.0' if running inside docker",
        default="127.0.0.1",
        json_schema_extra={"category": "Ray"},
    )

    BETA_TEMPLATE_NAMES: list[str] = Field(
        description="List of template names available in beta. These are currently made available via a Posthog feature"
        " flag",
        default_factory=list,
        json_schema_extra={"category": "Features"},
    )
    HALLUCINATION_CHECK: bool = Field(
        description="Should the LLM check for hallucinations? Note that the results of"
        " this are currently not surfaced in the UI",
        default=False,
        json_schema_extra={"category": "Features"},
    )

    # if using posthog
    POSTHOG_API_KEY: str | None = Field(
        description="PostHog API key for analytics", default=None, json_schema_extra={"category": "PostHog"}
    )
    POSTHOG_HOST: str = Field(
        description="PostHog service host URL",
        default="https://eu.i.posthog.com",
        json_schema_extra={"category": "PostHog"},
    )

    MIN_WORD_COUNT_FOR_SUMMARY: int = Field(
        default=200,
        description="Transcript must have at least this many words to be passed to summary stage",
        json_schema_extra={"category": "Content Filtering"},
    )
    MIN_WORD_COUNT_FOR_FULL_SUMMARY: int = Field(
        default=199,
        description=(
            "Transcript must have at least this many words to be passed to complex summary stage. "
            "Note, this is disabled by default as is lower than the MIN_WORD_COUNT_FOR_SUMMARY"
        ),
        json_schema_extra={"category": "Content Filtering"},
    )

    # use a dotenv file for local development
    if dotenv_detected:
        model_config = SettingsConfigDict(env_file=DOT_ENV_PATH, extra="ignore")


@lru_cache
def get_settings():
    return Settings()  # type: ignore  # noqa: PGH003

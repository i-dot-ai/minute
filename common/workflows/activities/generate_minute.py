"""Activity: generate a minute for a minute version (user-created minutes)."""

from uuid import UUID

from temporalio import activity
from temporalio.exceptions import ApplicationError

from common.services.minute_handler_service import (
    MinuteGenerationFailedError,
    MinuteGenerationTransientError,
    MinuteHandlerService,
)
from common.workflows import minute_version as wf


async def generate(minute_version_id: UUID) -> None:
    """Generate and persist the version's HTML; shared with the transcription workflow's summarise step."""
    try:
        await MinuteHandlerService.process_minute_generation_message(minute_version_id)
    except MinuteGenerationTransientError as e:
        raise ApplicationError(str(e)) from e  # dependency blip: retry
    except MinuteGenerationFailedError as e:
        # minute_version is already FAILED in the DB.
        raise ApplicationError(str(e.__cause__ or e), non_retryable=True) from e


@activity.defn(name=wf.GENERATE_MINUTE)
async def generate_minute(minute_version_id: str) -> None:
    await generate(UUID(minute_version_id))

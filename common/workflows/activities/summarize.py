"""Activity: generate the initial summary (same code the Ray LLM actor runs for MINUTE messages)."""

from uuid import UUID

from temporalio import activity
from temporalio.exceptions import ApplicationError

from common.services.minute_handler_service import MinuteDelivery, MinuteGenerationFailedError, MinuteHandlerService
from common.settings import get_structured_logger
from common.workflows import transcription as wf

slogger = get_structured_logger()


@activity.defn(name=wf.SUMMARIZE)
async def summarize(minute_id: str) -> None:
    slogger.refresh_context()
    slogger.set_context_field("minute_id", minute_id)
    try:
        minute_version = await MinuteHandlerService.get_only_minute_version_for_minute_id(UUID(minute_id))
    except ValueError as e:
        # Minute deleted with its transcription, or already edited: nothing to generate.
        raise ApplicationError(str(e), non_retryable=True) from e
    try:
        delivery = await MinuteHandlerService.process_minute_generation_message(minute_version.id)
    except MinuteGenerationFailedError as e:
        # minute_version is already FAILED in the DB.
        raise ApplicationError(str(e.__cause__ or e), non_retryable=True) from e
    if delivery == MinuteDelivery.LEAVE:
        msg = "Minute version claimed by an earlier attempt; retrying once the claim goes stale"
        raise ApplicationError(msg)

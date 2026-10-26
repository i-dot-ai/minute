"""Activity: generate the initial summary (same handler the SQS LLM queue used to run for MINUTE messages)."""

from uuid import UUID

from temporalio import activity
from temporalio.exceptions import ApplicationError

from common.services.minute_handler_service import MinuteHandlerService
from common.settings import get_structured_logger
from common.workflows import transcription as wf
from common.workflows.activities import generate_minute

slogger = get_structured_logger()


@activity.defn(name=wf.SUMMARISE)
async def summarise(minute_id: str) -> None:
    slogger.refresh_context()
    slogger.set_context_field("minute_id", minute_id)
    try:
        minute_version = await MinuteHandlerService.get_initial_minute_version_for_minute_id(UUID(minute_id))
    except ValueError as e:
        # Minute deleted with its transcription, or no initial version: nothing to generate.
        raise ApplicationError(str(e), non_retryable=True) from e
    await generate_minute.generate(minute_version.id)

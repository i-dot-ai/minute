"""Activity: apply an AI edit to a minute version."""

from uuid import UUID

from temporalio import activity
from temporalio.exceptions import ApplicationError

from common.services.minute_handler_service import (
    MinuteGenerationFailedError,
    MinuteGenerationTransientError,
    MinuteHandlerService,
)
from common.workflows import minute_version as wf


@activity.defn(name=wf.EDIT_MINUTE)
async def edit_minute(params: wf.MinuteEditInput) -> None:
    try:
        await MinuteHandlerService.process_minute_edit_message(
            target_minute_version_id=UUID(params.minute_version_id),
            source_minute_version_id=UUID(params.source_minute_version_id),
        )
    except MinuteGenerationTransientError as e:
        raise ApplicationError(str(e)) from e  # dependency blip: retry
    except MinuteGenerationFailedError as e:
        # target_minute_version is already FAILED in the DB.
        raise ApplicationError(str(e.__cause__ or e), non_retryable=True) from e

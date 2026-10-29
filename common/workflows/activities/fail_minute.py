"""Finalise minute generation and edits when Temporal exhausts the activity's retries."""

from uuid import UUID

from temporalio import activity

from common.services.minute_handler_service import MinuteHandlerService
from common.workflows import minute_version as minute_wf
from common.workflows import transcription as wf


@activity.defn(name=minute_wf.FAIL_MINUTE_VERSION)
async def fail_minute_version(params: minute_wf.FailMinuteInput) -> None:
    MinuteHandlerService.record_minute_version_failure(UUID(params.minute_version_id), params.error)


@activity.defn(name=wf.FAIL_SUMMARISE)
async def fail_summarise(params: wf.FailTranscriptionInput) -> None:
    try:
        version = await MinuteHandlerService.get_initial_minute_version_for_minute_id(UUID(params.minute_id))
    except ValueError:
        return  # deleted
    await fail_minute_version(minute_wf.FailMinuteInput(minute_version_id=str(version.id), error=params.error))

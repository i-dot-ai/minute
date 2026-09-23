import uuid
from datetime import UTC, datetime

from backend.api.dependencies import SQLSessionDep, UserDep
from backend.api.routes.minutes._queue import llm_queue_service
from backend.api.routes.minutes.get_minute import endpoint as get_minute
from common.database.postgres_models import JobStatus, MinuteVersion
from common.types import (
    EditMessageData,
    MinuteVersionCreateRequest,
    MinuteVersionResponse,
    TaskType,
    WorkerMessage,
)


async def endpoint(
    user: UserDep,
    session: SQLSessionDep,
    minute_id: uuid.UUID,
    req: MinuteVersionCreateRequest,
) -> MinuteVersionResponse:
    """Create a new minute version for a given minute, optionally with AI edit instructions."""

    minute = await get_minute(
        user=user,
        session=session,
        minute_id=minute_id,
    )

    minute_version = MinuteVersion(
        id=uuid.uuid4(),
        minute_id=minute.id,
        content_source=req.content_source,
        html_content=req.html_content,
        ai_edit_instructions=req.ai_edit_instructions.instruction if req.ai_edit_instructions else None,
        status=JobStatus.AWAITING_START if req.ai_edit_instructions else JobStatus.COMPLETED,
    )

    # Touched explicitly: adding a version leaves the minute row itself unchanged, so
    # the column's onupdate never fires and the list ordering would miss the edit.
    minute.updated_datetime = datetime.now(tz=UTC)
    session.add(minute_version)
    await session.commit()
    await session.refresh(minute_version)

    if req.ai_edit_instructions:
        llm_queue_service.publish_message(
            WorkerMessage(
                id=minute_version.id,
                data=EditMessageData(source_id=req.ai_edit_instructions.source_id),
                type=TaskType.EDIT,
            )
        )
    return MinuteVersionResponse(
        id=minute_version.id,
        minute_id=minute_id,
        status=minute_version.status,
        created_datetime=minute_version.created_datetime,
        updated_datetime=minute_version.updated_datetime,
        error=minute_version.error,
        ai_edit_instructions=minute_version.ai_edit_instructions,
        html_content=minute_version.html_content,
        content_source=minute_version.content_source,
    )

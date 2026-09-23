import uuid

from fastapi import HTTPException, status

from backend.api.dependencies import SQLSessionDep, UserDep
from backend.api.routes.minutes._queue import llm_queue_service
from common.database.postgres_models import Minute, MinuteVersion, Transcription
from common.types import MinuteListItem, MinutesCreateRequest, TaskType, WorkerMessage


async def endpoint(
    user: UserDep,
    session: SQLSessionDep,
    transcription_id: uuid.UUID,
    req: MinutesCreateRequest,
) -> MinuteListItem:
    """Create a new minute for a given transcription, optionally based on a source minute."""

    transcription = await session.get(Transcription, transcription_id)
    if not transcription or (transcription.user_id != user.id):
        msg = f"Transcription {transcription_id} not found for user {user.id}"
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=msg)

    if req.source_minute_id:
        source_minute = await session.get(Minute, req.source_minute_id)
        if not source_minute or source_minute.transcription_id != transcription_id:
            msg = f"Source minute {req.source_minute_id} not found for transcription {transcription_id}"
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=msg)
        template_name = source_minute.template_name
        user_template_id = source_minute.user_template_id
        agenda = source_minute.agenda

    else:
        template_name = req.template_name
        user_template_id = req.template_id
        agenda = req.agenda

    minute = Minute(
        transcription_id=transcription_id,
        # Already validated in the request model, so we can safely assign it here
        template_name=template_name, # pyright: ignore[reportArgumentType]
        agenda=agenda,
        user_template_id=user_template_id,
    )

    session.add(minute)
    minute_version = MinuteVersion(id=uuid.uuid4(), minute_id=minute.id)
    session.add(minute_version)
    await session.commit()
    await session.refresh(minute_version)
    await session.refresh(minute)

    llm_queue_service.publish_message(
        WorkerMessage(
            id=minute_version.id,
            type=TaskType.MINUTE,
        )
    )

    return MinuteListItem(
        id=minute.id,
        created_datetime=minute.created_datetime,
        updated_datetime=minute.updated_datetime,
        transcription_id=minute.transcription_id,
        template_name=minute.template_name,
        agenda=minute.agenda,
    )

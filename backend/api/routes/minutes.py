import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, HTTPException
from sqlalchemy.orm import selectinload
from sqlmodel import col, select

from backend.api.dependencies import SQLSessionDep, UserDep
from common.database.postgres_models import JobStatus, Minute, MinuteVersion, Transcription
from common.services.queue_services import get_queue_service
from common.settings import get_settings
from common.types import (
    EditMessageData,
    MinuteListItem,
    MinutesCreateRequest,
    MinuteVersionCreateRequest,
    MinuteVersionResponse,
    TaskType,
    WorkerMessage,
)

settings = get_settings()

queue_service = get_queue_service(settings.QUEUE_SERVICE_NAME)

minutes_router = APIRouter(tags=["Minutes"])


@minutes_router.get("/transcription/{transcription_id}/minutes")
async def list_minutes_for_transcription(
    transcription_id: uuid.UUID, session: SQLSessionDep, user: UserDep
) -> list[MinuteListItem]:
    transcription = await session.get(Transcription, transcription_id)
    if not transcription or transcription.user_id != user.id:
        raise HTTPException(404, "Not found")

    query = (
        select(Minute).where(Minute.transcription_id == transcription_id).order_by(col(Minute.updated_datetime).desc())
    )
    result = await session.exec(query)
    minutes = result.all()
    return [
        MinuteListItem(
            id=minute.id,
            created_datetime=minute.created_datetime,
            updated_datetime=minute.updated_datetime,
            transcription_id=minute.transcription_id,
            template_name=minute.template_name,
            agenda=minute.agenda,
        )
        for minute in minutes
    ]


@minutes_router.post("/transcription/{transcription_id}/minutes")
async def create_minute(
    transcription_id: uuid.UUID, request: MinutesCreateRequest, session: SQLSessionDep, user: UserDep
):
    transcription = await session.get(Transcription, transcription_id)
    if not transcription or transcription.user_id != user.id:
        raise HTTPException(404, "Not found")
    minute = Minute(
        transcription_id=transcription_id,
        template_name=request.template_name,
        agenda=request.agenda,
        user_template_id=request.template_id,
    )
    session.add(minute)
    minute_version = MinuteVersion(id=uuid.uuid4(), minute_id=minute.id)
    session.add(minute_version)
    await session.commit()
    await session.refresh(minute_version)
    queue_service.publish_message(WorkerMessage(id=minute_version.id, type=TaskType.MINUTE))


@minutes_router.get("/minutes/{minutes_id}")
async def get_minute(minutes_id: uuid.UUID, session: SQLSessionDep, user: UserDep) -> Minute:
    query = (
        select(Minute)
        .where(Minute.id == minutes_id)
        .options(selectinload(Minute.transcription), selectinload(Minute.minute_versions))
    )
    result = await session.exec(query)
    minute = result.first()
    if not minute or not minute.transcription.user_id or minute.transcription.user_id != user.id:
        raise HTTPException(404, "Not found")

    return minute


@minutes_router.get("/minutes/{minute_id}/versions")
async def list_minute_versions(
    minute_id: uuid.UUID, session: SQLSessionDep, user: UserDep
) -> list[MinuteVersionResponse]:
    result = await session.exec(
        select(Minute)
        .where(Minute.id == minute_id)
        .options(selectinload(Minute.minute_versions), selectinload(Minute.transcription))
    )
    minute = result.first()
    if not minute or not minute.transcription.user_id or minute.transcription.user_id != user.id:
        raise HTTPException(404)

    return [
        MinuteVersionResponse(
            id=version.id,
            minute_id=minute_id,
            status=version.status,
            created_datetime=version.created_datetime,
            error=version.error,
            ai_edit_instructions=version.ai_edit_instructions,
            html_content=version.html_content,
            content_source=version.content_source,
        )
        for version in minute.minute_versions
    ]


@minutes_router.post("/minutes/{minute_id}/versions")
async def create_minute_version(
    minute_id: uuid.UUID, request: MinuteVersionCreateRequest, session: SQLSessionDep, user: UserDep
) -> MinuteVersionResponse:
    minute = await get_minute(minute_id, session, user)
    minute_version = MinuteVersion(
        id=uuid.uuid4(),
        minute_id=minute.id,
        content_source=request.content_source,
        html_content=request.html_content,
        ai_edit_instructions=request.ai_edit_instructions.instruction if request.ai_edit_instructions else None,
        status=JobStatus.AWAITING_START if request.ai_edit_instructions else JobStatus.COMPLETED,
    )
    minute.updated_datetime = datetime.now(tz=UTC)
    session.add(minute_version)
    await session.commit()
    await session.refresh(minute_version)
    if request.ai_edit_instructions:
        queue_service.publish_message(
            WorkerMessage(
                id=minute_version.id,
                data=EditMessageData(source_id=request.ai_edit_instructions.source_id),
                type=TaskType.EDIT,
            )
        )
    return MinuteVersionResponse(
        id=minute_version.id,
        minute_id=minute_id,
        status=minute_version.status,
        created_datetime=minute_version.created_datetime,
        error=minute_version.error,
        ai_edit_instructions=minute_version.ai_edit_instructions,
        html_content=minute_version.html_content,
        content_source=minute_version.content_source,
    )


@minutes_router.get("/minute_versions/{minute_version_id}")
async def get_minute_version(minute_version_id: uuid.UUID, session: SQLSessionDep, user: UserDep) -> MinuteVersion:
    query = (
        select(MinuteVersion)
        .where(MinuteVersion.id == minute_version_id)
        .options(selectinload(MinuteVersion.minute).selectinload(Minute.transcription))
    )
    minute_version = (await session.exec(query)).first()
    if (
        not minute_version
        or not minute_version.minute.transcription.user_id
        or minute_version.minute.transcription.user_id != user.id
    ):
        raise HTTPException(404, "Not found")

    return minute_version


@minutes_router.delete("/minute_versions/{minute_version_id}")
async def delete_minute_version(minute_version_id: uuid.UUID, session: SQLSessionDep, user: UserDep):
    query = (
        select(MinuteVersion)
        .where(MinuteVersion.id == minute_version_id)
        .options(selectinload(MinuteVersion.minute).selectinload(Minute.transcription))
    )
    minute_version = (await session.exec(query)).first()
    if (
        not minute_version
        or not minute_version.minute.transcription.user_id
        or minute_version.minute.transcription.user_id != user.id
    ):
        raise HTTPException(404, "Not found")

    await session.delete(minute_version)
    await session.commit()

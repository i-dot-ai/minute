import logging
import uuid

from fastapi import APIRouter, HTTPException
from sqlalchemy import delete
from sqlmodel import col, select

from backend.api.dependencies import SQLSessionDep, UserDep
from backend.app.minutes.types import (
    ChatCreateRequest,
    ChatCreateResponse,
    ChatGetAllResponse,
    ChatGetResponse,
    TaskType,
    WorkerMessage,
)
from backend.services.queue_services import get_queue_service
from common.database.postgres_models import (
    Chat,
    Transcription,
)
from common.settings import get_settings

settings = get_settings()
chat_router = APIRouter(tags=["Chat"])
queue_service = get_queue_service(settings.QUEUE_SERVICE_NAME)

logger = logging.getLogger(__name__)


@chat_router.get("/transcriptions/{transcription_id}/chat", response_model=ChatGetAllResponse)
async def list_chat(
    transcription_id: uuid.UUID,
    session: SQLSessionDep,
    current_user: UserDep,
) -> ChatGetAllResponse:
    transcription = await session.get(Transcription, transcription_id)
    if not transcription or transcription.user_id != current_user.id:
        raise HTTPException(404, "Not found")

    query = select(Chat).where(Chat.transcription_id == transcription_id).order_by(col(Chat.updated_datetime).asc())
    result = await session.exec(query)
    chats = result.all()

    return ChatGetAllResponse(
        chat=[
            ChatGetResponse(
                id=chat.id,
                created_datetime=chat.created_datetime,
                updated_datetime=chat.updated_datetime,
                user_content=chat.user_content,
                assistant_content=chat.assistant_content,
                status=chat.status,
            )
            for chat in chats
        ]
    )


@chat_router.post("/transcriptions/{transcription_id}/chat", response_model=ChatCreateResponse, status_code=201)
async def create_chat(
    transcription_id: uuid.UUID,
    request: ChatCreateRequest,
    session: SQLSessionDep,
    current_user: UserDep,
) -> ChatCreateResponse:
    transcription = await session.get(Transcription, transcription_id)
    if not transcription or transcription.user_id != current_user.id:
        raise HTTPException(404, "Not found")
    chat_id = uuid.uuid4()
    chat = Chat(user_content=request.user_content, transcription_id=transcription_id, id=chat_id)
    session.add(chat)
    await session.commit()
    await session.refresh(chat)
    queue_service.publish_message(WorkerMessage(id=chat.id, type=TaskType.INTERACTIVE))
    return ChatCreateResponse(id=chat.id)


@chat_router.get("/transcriptions/{transcription_id}/chat/{chat_id}", response_model=ChatGetResponse)
async def get_chat(
    transcription_id: uuid.UUID,
    chat_id: uuid.UUID,
    session: SQLSessionDep,
    current_user: UserDep,
) -> ChatGetResponse:
    transcription = await session.get(Transcription, transcription_id)
    if not transcription or transcription.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Transcription not found")

    chat = await session.get(Chat, chat_id)
    return ChatGetResponse(
        id=chat.id,
        created_datetime=chat.created_datetime,
        updated_datetime=chat.updated_datetime,
        user_content=chat.user_content,
        assistant_content=chat.assistant_content,
        status=chat.status,
    )


@chat_router.delete("/transcriptions/{transcription_id}/chat/{chat_id}", status_code=204)
async def delete_chat(transcription_id: uuid.UUID, chat_id: uuid.UUID, session: SQLSessionDep, current_user: UserDep):
    """Delete a specific transcription by ID."""
    # First check if the transcription exists and belongs to the user
    transcription = await session.get(Transcription, transcription_id)
    if not transcription or transcription.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Transcription not found")
    chat = await session.get(Chat, chat_id)
    # Delete the transcription
    await session.delete(chat)
    await session.commit()


@chat_router.delete("/transcriptions/{transcription_id}/chat", status_code=204)
async def delete_chats(transcription_id: uuid.UUID, session: SQLSessionDep, current_user: UserDep):
    # First check if the transcription exists and belongs to the user
    transcription = await session.get(Transcription, transcription_id)
    if not transcription or transcription.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Transcription not found")
    await session.execute(delete(Chat).where(Chat.transcription_id == transcription_id))

    # Delete the transcription
    await session.commit()

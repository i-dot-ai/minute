"""Interactive chat processing.

Extracted from TranscriptionHandlerService so that the LLM worker can process
interactive chat messages without importing the transcription service stack
(TranscriptionServiceManager pulls in azure.storage.blob and ffmpeg). This module
only depends on the LLM client, the database layer and citation formatting.
"""

import logging
from uuid import UUID

from sqlalchemy.orm import selectinload
from sqlmodel import col, select

from common.database.postgres_database import SessionLocal
from common.database.postgres_models import Chat, JobStatus
from common.llm.client import FastOrBestLLM, create_default_chatbot
from common.prompts import get_chat_with_transcript_system_message
from common.services.exceptions import InteractionFailedError
from common.templates.citations import combine_consecutive_citations

logger = logging.getLogger(__name__)


async def process_interactive_message(chat_id: UUID) -> None:
    """Process an interactive message from the LLM and return the result."""
    try:
        chatbot = create_default_chatbot(FastOrBestLLM.FAST)
        with SessionLocal() as session:
            chat = session.get(Chat, chat_id)

            if not chat:
                msg = f"Chat id {chat_id} not found"
                raise InteractionFailedError(msg)

            query = (
                select(Chat)
                .where(Chat.transcription_id == chat.transcription_id)
                .order_by(col(Chat.updated_datetime).asc())
                .options(selectinload(Chat.transcription))
            )
            result = session.exec(query)
            chats = result.all()

            chat_history = [get_chat_with_transcript_system_message(chat.transcription.dialogue_entries)]
            for entry in chats:
                chat_history.append(
                    {
                        "role": "user",
                        "content": entry.user_content,
                    }
                )
                if entry.assistant_content:
                    chat_history.append(
                        {
                            "role": "assistant",
                            "content": entry.assistant_content,
                        }
                    )

            chat_response = await chatbot.chat(messages=chat_history)
            chat_response = combine_consecutive_citations(chat_response)
            chat.assistant_content = chat_response
            chat.status = JobStatus.COMPLETED

            session.add(chat)
            session.commit()
    except Exception as e:
        msg = f"Chat interaction failed: {e!s}"
        logger.exception(msg)
        try:
            chat.status = JobStatus.FAILED
            chat.error = msg
            session.add(chat)
            session.commit()
        except Exception:
            logger.exception("Error updating chat status. Maybe it doesn't exist?")

        raise InteractionFailedError from e

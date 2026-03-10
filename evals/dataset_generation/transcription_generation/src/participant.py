from abc import abstractmethod
from functools import cached_property

from pydantic import BaseModel

from common.llm.client import ChatBot, FastOrBestLLM, create_default_chatbot

from .constants import ACTOR_SYSTEM_TEMPLATE, get_template


class ChatEntry(BaseModel):
    speaker_id: str
    content: str


class HistoryManager:
    def __init__(self) -> None:
        self.history: list[ChatEntry] = []

    def add_to_history(self, content: str, origin_speaker_id: str) -> None:
        self.history.append(ChatEntry(speaker_id=origin_speaker_id, content=content))

    def get_history_for_participant(self, speaker_id: str) -> list[dict]:
        prepared_history = []
        for entry in self.history:
            if entry.speaker_id == speaker_id:
                prepared_history.append({"role": "assistant", "content": entry.content})
            else:
                prepared_history.append({"role": "user", "content": entry.content})
        return prepared_history


class Participant:
    def __init__(self, identifier: str, history_manager: HistoryManager, chatbot: ChatBot | None = None) -> None:
        self.identifier = identifier
        self.history_manager = history_manager
        self.chatbot = chatbot or create_default_chatbot(FastOrBestLLM.FAST)

    @property
    @abstractmethod
    def system_message_content(self) -> str:
        pass

    def full_history(self, notice_message: str):
        system_message = {
            "role": "system",
            "content": self.system_message_content,
        }
        messages_history = self.history_manager.get_history_for_participant(self.identifier)
        return [system_message, *messages_history, {"role": "user", "content": notice_message}]


class Actor(Participant):
    def __init__(
        self, identifier: str, history_manager: HistoryManager, actor_definition: str, chatbot: ChatBot | None = None
    ) -> None:
        super().__init__(identifier, history_manager, chatbot)
        self.actor_definition = actor_definition

    @cached_property
    def system_message_content(self) -> str:
        template = get_template(ACTOR_SYSTEM_TEMPLATE)
        return template.render(role_definition=self.actor_definition)

    async def reply_to_last_message(self, notice_message: str) -> str:
        messages = self.full_history(notice_message)
        response = await self.chatbot.chat(messages)
        self.history_manager.add_to_history(response, self.identifier)
        return response

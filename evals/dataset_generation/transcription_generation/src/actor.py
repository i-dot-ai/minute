import re
from functools import cached_property

from common.llm.client import ChatBot

from .constants import ACTOR_SYSTEM_TEMPLATE, get_template
from .history_manager import HistoryManager
from .participant import Participant


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

    async def reply_to_last_message(self, notice_message: str | None = None) -> str:
        messages = self.get_new_messages(notice_message)
        response = await self.chatbot.chat(messages)
        cleaned_response = re.sub(r"^speaker_\d+\s+said:\s*", "", response, flags=re.IGNORECASE)
        self.history_manager.add_to_history(cleaned_response, self.identifier)
        return cleaned_response

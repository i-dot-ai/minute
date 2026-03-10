from pydantic import BaseModel

from common.llm.client import ChatBot, FastOrBestLLM, create_default_chatbot


class ChatEntry(BaseModel):
    role: str
    content: str


class Participant:
    def __init__(self, chatbot: ChatBot | None = None) -> None:
        self.history: list[ChatEntry] = []
        self.chatbot = chatbot or create_default_chatbot(FastOrBestLLM.FAST)

    def add_to_history(self, entry: ChatEntry):
        self.history.append(entry)


class Actor(Participant):
    def __init__(self, identifier: str, chatbot: ChatBot | None = None) -> None:
        super().__init__(chatbot)
        self.identifier = identifier

    async def reply_to_last_message(self) -> str:
        messages = [entry.model_dump() for entry in self.history]
        return await self.chatbot.chat(messages)

    def __str__(self) -> str:
        return f"Actor {self.identifier}"

from abc import abstractmethod

from common.llm.client import ChatBot, FastOrBestLLM, create_default_chatbot

from evals.dataset_generation.transcription_generation.src.history_manager import HistoryManager


class Participant:
    def __init__(self, identifier: str, history_manager: HistoryManager, chatbot: ChatBot | None = None) -> None:
        self.identifier = identifier
        self.history_manager = history_manager
        self.chatbot = chatbot or create_default_chatbot(FastOrBestLLM.FAST)

    @property
    @abstractmethod
    def system_message_content(self) -> str:
        pass

    def get_new_messages(self, notice_message: str | None = None) -> list[dict]:
        full_history = []

        full_history.append(
            {
                "role": "system",
                "content": self.system_message_content,
            }
        )
        full_history.extend(self.history_manager.get_history_for_participant(self.identifier))
        if notice_message:
            full_history.append({"role": "user", "content": notice_message})

        # remove messages that were already stored by the chatbot
        return full_history[len(self.chatbot.messages) :]

from .models import ChatEntry


class HistoryManager:
    def __init__(self) -> None:
        self.history: list[ChatEntry] = []

    def add_to_history(self, content: str, origin_speaker_id: str) -> None:
        self.history.append(ChatEntry(speaker_id=origin_speaker_id, content=content))

    def get_history_for_participant(self, speaker_id: str) -> list[dict]:
        prepared_history = []
        for entry in self.history:
            if entry.speaker_id == speaker_id:
                prepared_history.append({"role": "assistant", "content": f"You said: {entry.content}"})
            else:
                prepared_history.append({"role": "user", "content": f"{entry.speaker_id} said: {entry.content}"})
        return prepared_history

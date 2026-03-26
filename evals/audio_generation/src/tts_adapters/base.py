from abc import ABC, abstractmethod


class TTSAdapter(ABC):
    @abstractmethod
    def text_to_speech(self, text: str, voice_id: str) -> bytes:
        """Convert text to speech and return audio bytes."""

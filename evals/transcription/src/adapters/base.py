from abc import ABC, abstractmethod
from typing import Any


class TranscriptionAdapter(ABC):
    @abstractmethod
    def transcribe(self, wav_path: str) -> tuple[str, float]:
        pass

    @abstractmethod
    def transcribe_with_debug(self, wav_path: str) -> tuple[str, float, dict[str, Any]]:
        pass

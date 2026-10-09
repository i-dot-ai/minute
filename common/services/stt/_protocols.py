"""Transcription service contract."""

from pathlib import Path
from typing import Protocol

from common.database.postgres_models import DialogueEntry


class TranscriptionFailedError(Exception):
    """Raised when a transcription service cannot produce a transcript."""


class STT(Protocol):
    """Contract for a speech-to-text provider.

    Structural: any provider (and test doubles) conform without inheriting.
    """

    async def transcribe(self, audio_file_path: Path) -> list[DialogueEntry]:
        """Transcribe a local audio file into dialogue entries.

        :param audio_file_path: Local audio file to transcribe.
        :returns: Dialogue entries in chronological order.
        :raises TranscriptionFailedError: If transcription fails.
        """
        ...

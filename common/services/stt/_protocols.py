"""Transcription service contract."""

from pathlib import Path
from typing import Protocol

from common.types import DialogueEntry


class TranscriptionFailedError(Exception):
    """Raised when a transcription service cannot produce a transcript."""


class TranscriptionTransientError(Exception):
    """Raised when the provider couldn't take the request right now (throttled, 5xx, timeout,
    network): the same audio may well succeed later, so the caller should retry with backoff."""


class STT(Protocol):
    """Contract for a speech-to-text provider.

    Structural: any provider (and test doubles) conform without inheriting.
    """

    async def transcribe(
        self, audio_file_path: Path, timeout_seconds: float = ..., attempt: int = ...
    ) -> list[DialogueEntry]:
        """Transcribe a local audio file into dialogue entries.

        One attempt: transient provider failures raise, and the caller (Temporal) retries.

        :param audio_file_path: Local audio file to transcribe.
        :param timeout_seconds: Total time budget for this call.
        :param attempt: 1-based attempt number. A provider with several endpoints (e.g. regions)
            uses it to pick one, so the caller's retry policy walks them instead of the provider.
        :returns: Dialogue entries in chronological order.
        :raises TranscriptionTransientError: If the provider was unavailable; retry later.
        :raises TranscriptionFailedError: If transcription fails and retrying won't help.
        """
        ...

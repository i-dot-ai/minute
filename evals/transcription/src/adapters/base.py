import asyncio
import logging
import time
from abc import ABC, abstractmethod
from pathlib import Path
from typing import TypedDict

from common.services.transcription_services.adapter import (
    TranscriptionAdapter as CommonTranscriptionAdapter,
)

from evals.transcription.src.models import TranscriptionResult

logger = logging.getLogger(__name__)


class EvalsTranscriptionAdapter(ABC):
    """
    Abstract base class for transcription adapters used in evaluations.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Name of the transcription adapter."""
        pass

    @abstractmethod
    def transcribe(self, wav_path: str) -> TranscriptionResult:
        """Transcribe the given wav file."""
        pass


class ServiceTranscriptionAdapter(EvalsTranscriptionAdapter):
    """
    Adapter wrapping common transcription services for evaluation use.
    """

    def __init__(self, service_adapter: type[CommonTranscriptionAdapter], service_name: str):
        """
        Initializes the service transcription adapter with the given adapter class and name.
        """
        self._adapter = service_adapter
        self._service_name = service_name

    @property
    def name(self) -> str:
        """
        Returns the name of the transcription service.
        """
        return self._service_name

    def transcribe(self, wav_path: str) -> TranscriptionResult:
        """
        Transcribes the audio file at the given path and returns the result with timing information.
        """
        start_time = time.time()

        try:
            result = asyncio.run(self._adapter.start(Path(wav_path)))
            end_time = time.time()

            dialogue_entries = result.transcript

            if not dialogue_entries:
                logger.error("%s returned an empty transcript for %s", self._service_name, wav_path)
                return TranscriptionResult(
                    text="",
                    duration_sec=(end_time - start_time),
                    debug_info={"error": "Empty transcript"},
                )

            full_text = " ".join(entry["text"] for entry in dialogue_entries).strip()

            return TranscriptionResult(
                text=full_text,
                duration_sec=(end_time - start_time),
                debug_info={},
            )

        except Exception as error:
            logger.error("%s transcription failed: %s", self._service_name, error)
            end_time = time.time()
            return TranscriptionResult(
                text="",
                duration_sec=(end_time - start_time),
                debug_info={"error": str(error)},
            )


class AdapterConfig(TypedDict):
    """Configuration for a transcription adapter."""

    adapter: EvalsTranscriptionAdapter

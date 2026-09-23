from abc import ABC, abstractmethod
from pathlib import Path

from common.database.postgres_models import Recording
from common.types import TranscriptionJobMessageData


class _STT(ABC):
    """Base class for the Azure speech-to-text adapters.

    There are exactly two implementations, selected purely by audio length:
    `AzureSTT` (synchronous, short audio) and `AzureSTTBatch` (asynchronous,
    long audio). The base class exists only to give the manager a common
    `name` / `start` / `check` contract.

    `name` is the stable identifier serialised onto the queue message
    (`TranscriptionJobMessageData.transcription_service`) so an async job can be
    resumed by name after it comes back off the queue.
    """

    name: str

    @classmethod
    @abstractmethod
    async def start(cls, audio_file_path_or_recording: Path | Recording) -> TranscriptionJobMessageData:
        """Start a transcription job.

        Synchronous adapters take a local `Path` and return a completed job (with
        `transcript` populated). Asynchronous adapters take a `Recording`, submit
        the job to the provider, and return a job handle (no transcript yet).
        """
        ...

    @classmethod
    @abstractmethod
    async def check(cls, data: TranscriptionJobMessageData) -> TranscriptionJobMessageData:
        """Check/advance a transcription job.

        Synchronous adapters simply return `data` unchanged (the transcript is
        already present). Asynchronous adapters poll the provider and, when the
        job has finished, return `data` with `transcript` populated; if it is
        still running they return `data` unchanged so the caller can re-queue.
        """
        ...


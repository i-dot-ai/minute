from abc import ABC, abstractmethod
from enum import Enum, auto
from pathlib import Path
from typing import overload

from common.database.postgres_models import Recording
from common.types import TranscriptionJobMessageData


class AdapterType(Enum):
    SYNCHRONOUS = auto()
    ASYNC = auto()


class TranscriptionAdapter(ABC):
    """Abstract base class for transcription adapters.

    This class defines a contract for transcription adapters that interact with
    external transcription services. It sets the required attributes
    and methods that subclasses must implement to provide transcription
    functionality. Subclasses must implement attributes and methods to determine availability,
    start a transcription process, and check transcription status.

    New Adapter implementations are discovered via inspection and are dynamically loaded (as long as they are
    in the same package as the Adapter class).

    Attributes:
        max_audio_length (int): Defines the maximum supported length of an audio
            file in seconds for transcription.
        name (str): Name identifier for the transcription adapter.
        adapter_type (AdapterType): Specifies the type of adapter (synchronous or asynchronous).
    """

    max_audio_length: int
    name: str
    adapter_type: AdapterType

    @classmethod
    @abstractmethod
    def is_available(cls) -> bool:
        """Determines if the functionality is available.

        This class method is abstract and must be implemented by subclasses to
        specify whether the required functionality is available in the current
        context.

        Returns:
            bool: True if the functionality is available, False otherwise.
        """
        ...

    @classmethod
    @overload
    async def start(cls, audio_file_path_or_recording: Path) -> TranscriptionJobMessageData:
        """Starts a transcription job asynchronously.

        This method begins the transcription process for the given audio file path
        or recording. It supports asynchronous execution and allows handling of
        transcription tasks with flexibility in input types.

        Args:
            audio_file_path_or_recording:
                A Path object representing the file path to the audio or a
                recording to be processed.

        Returns:
            A TranscriptionJobMessageData object containing information about the
            transcription job that was started.
        """

    @classmethod
    @overload
    async def start(cls, audio_file_path_or_recording: Recording) -> TranscriptionJobMessageData:
        """Starts a transcription job asynchronously.

        This method begins the transcription process for the given audio file path
        or recording. It supports asynchronous execution and allows handling of
        transcription tasks with flexibility in input types.

        Args:
            audio_file_path_or_recording:
                A Recording object representing the file path to the audio or a
                recording to be processed.

        Returns:
            A TranscriptionJobMessageData object containing information about the
            transcription job that was started.
        """

    @classmethod
    @abstractmethod
    async def start(cls, audio_file_path_or_recording: Path | Recording) -> TranscriptionJobMessageData: ...

    @classmethod
    @abstractmethod
    async def check(cls, data: TranscriptionJobMessageData) -> TranscriptionJobMessageData:
        """
        Defines an abstract class method to check and process transcription job message data.

        In the case of AdapterType.SYNCHRONOUS this should simply return the data argument, as this should already have
        the TranscriptionJobMessageData.transcript populated.

        In the case of AdapterType.ASYNCHRONOUS this should check the status of the transcription job and update the
        TranscriptionJobMessageData.transcript field with the transcribed data, if available."""
        ...

from .azure import AzureSTTAdapter
from .base import TranscriptionAdapter
from .whisper import WhisperAdapter

__all__ = ["AzureSTTAdapter", "TranscriptionAdapter", "WhisperAdapter"]

from common.services.transcription_services.whisply_local import WhisplyLocalAdapter

from evals.transcription.src.adapters.base import ServiceTranscriptionAdapter


def WhisperAdapter() -> ServiceTranscriptionAdapter:
    """
    Creates and returns a Whisply local adapter for evaluation use.
    """
    return ServiceTranscriptionAdapter(WhisplyLocalAdapter, "Whisply")

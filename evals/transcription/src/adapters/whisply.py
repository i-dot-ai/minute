from common.services.transcription_services.whisply_local import (
    WhisplyLocalAdapter as CommonWhisplyAdapter,
)
from evals.transcription.src.adapters.base import ServiceTranscriptionAdapter


def whisply_adapter() -> ServiceTranscriptionAdapter:
    return ServiceTranscriptionAdapter(CommonWhisplyAdapter, "Whisply")

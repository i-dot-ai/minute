from common.services.stt._protocols import STT, TranscriptionFailedError
from common.services.stt.azure import Azure


def get_transcription_service() -> STT:
    return Azure()


__all__ = [
    "STT",
    "Azure",
    "TranscriptionFailedError",
    "get_transcription_service",
]

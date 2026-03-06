from common.services.transcription_services.adapter import TranscriptionAdapter
from common.services.transcription_services.azure import AzureSpeechAdapter
from common.services.transcription_services.whisply_local import WhisplyLocalAdapter

ADAPTER_REGISTRY: dict[str, tuple[type[TranscriptionAdapter], str]] = {
    "azure": (AzureSpeechAdapter, "Azure Speech-to-Text"),
    "whisply": (WhisplyLocalAdapter, "Whisper"),
}

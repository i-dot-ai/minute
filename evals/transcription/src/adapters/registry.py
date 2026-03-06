from common.services.transcription_services.azure import AzureSpeechAdapter
from common.services.transcription_services.whisply_local import WhisplyLocalAdapter
from evals.transcription.src.adapters.base import ServiceTranscriptionAdapter

ADAPTER_REGISTRY: dict[str, ServiceTranscriptionAdapter] = {
    "azure": ServiceTranscriptionAdapter(AzureSpeechAdapter, "Azure Speech API"),
    "whisply": ServiceTranscriptionAdapter(WhisplyLocalAdapter, "Whisply"),
}

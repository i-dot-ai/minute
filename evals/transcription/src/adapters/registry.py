from typing import Callable

from common.services.transcription_services.azure import AzureSpeechAdapter
from common.services.transcription_services.whisply_local import WhisplyLocalAdapter

from evals.transcription.src.adapters.base import ServiceTranscriptionAdapter

ADAPTER_REGISTRY: dict[str, Callable[[], ServiceTranscriptionAdapter]] = {
    "azure": lambda: ServiceTranscriptionAdapter(AzureSpeechAdapter, "Azure Speech API"),
    "whisply": lambda: ServiceTranscriptionAdapter(WhisplyLocalAdapter, "Whisply"),
}


def get_adapter(name: str) -> ServiceTranscriptionAdapter:
    """
    Creates and returns a transcription adapter by name.
    """
    if name not in ADAPTER_REGISTRY:
        available = ", ".join(ADAPTER_REGISTRY.keys())
        msg = f"Unknown adapter '{name}'. Available adapters: {available}"
        raise ValueError(msg)
    return ADAPTER_REGISTRY[name]()


def list_adapters() -> list[str]:
    """
    Returns list of available adapter names.
    """
    return list(ADAPTER_REGISTRY.keys())

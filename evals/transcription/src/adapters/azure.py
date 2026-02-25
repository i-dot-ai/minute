from common.services.transcription_services.azure import AzureSpeechAdapter as CommonAzureAdapter

from evals.transcription.src.adapters.base import ServiceTranscriptionAdapter


def AzureSTTAdapter() -> ServiceTranscriptionAdapter:
    """
    Creates and returns an Azure Speech-to-Text adapter for evaluation use.
    """
    return ServiceTranscriptionAdapter(CommonAzureAdapter, "Azure Speech API")

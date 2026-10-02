import logging
import tempfile
from pathlib import Path

import sentry_sdk

from common.convert_american_to_british_spelling import convert_american_to_british_spelling
from common.database.postgres_models import Transcription
from common.services.exceptions import TranscriptionFailedError
from common.services.storage_services import get_storage_service
from common.services.transcription_services.adapter import AdapterType, TranscriptionAdapter
from common.services.transcription_services.aws import AWSTranscribeAdapter
from common.services.transcription_services.azure import AzureSpeechAdapter
from common.services.transcription_services.azure_async import AzureBatchTranscriptionAdapter
from common.settings import get_settings
from common.types import TranscriptionJobMessageData

logger = logging.getLogger(__name__)

settings = get_settings()
# add any new adapters here
_adapters = {
    adapter.name: adapter for adapter in [AzureSpeechAdapter, AWSTranscribeAdapter, AzureBatchTranscriptionAdapter]
}
storage_service = get_storage_service(get_settings().STORAGE_SERVICE_NAME)


class TranscriptionServiceManager:
    """Manager class that handles switching between different transcription adapters."""

    def __init__(self):
        self._available_adapters = self.get_available_services()

    def get_available_services(self) -> dict[str, TranscriptionAdapter]:
        """Get list of available (properly configured) services."""
        adapters = {}
        for adapter_name in settings.TRANSCRIPTION_SERVICES:
            adapter = _adapters.get(adapter_name)
            if not adapter:
                logger.warning("Adapter not found %s", adapter_name)
            elif not adapter.is_available():
                logger.warning("Transcription service %s is not available", adapter.name)
            else:
                logger.info("registered transcription service %s", adapter.name)
                adapters[adapter.name] = adapter
        if not adapters:
            logger.warning("No transcription services are available")

        return adapters

    def select_adaptor(self, duration_seconds: int) -> TranscriptionAdapter:
        for adaptor in self._available_adapters.values():
            if adaptor.max_audio_length >= duration_seconds:
                return adaptor
        msg = f"No transcription services are available. Available services: {self._available_adapters}"
        raise RuntimeError(msg)

    async def check_transcription(
        self, adapter_name: str, async_transcription_message_data: TranscriptionJobMessageData
    ) -> TranscriptionJobMessageData:
        adapter = self._available_adapters.get(adapter_name)
        if not adapter or not adapter.is_available():
            msg = f"Transcription service {adapter_name} is not available"
            raise TranscriptionFailedError(msg)
        transcription_job = await adapter.check(async_transcription_message_data)
        if transcription_job.transcript:
            for entry in transcription_job.transcript:
                entry["text"] = convert_american_to_british_spelling(entry["text"])
        return transcription_job

    async def perform_transcription_steps(
        self, transcription: Transcription, duration_seconds: float
    ) -> TranscriptionJobMessageData:
        """Transcribe an already-converted recording.

        The audio worker has already converted the source to a mono mp3 and created the
        corresponding Recording row, so recordings[0] is transcription-ready and the duration
        is supplied by the caller (no ffprobe here).
        """
        recording = transcription.recordings[0]
        with tempfile.TemporaryDirectory() as tempdir:
            file_path = Path(tempdir) / Path(recording.s3_file_key).name
            await storage_service.download(recording.s3_file_key, file_path)
            with sentry_sdk.start_transaction(
                op="process", name="collect_file_metadata_before_transcription"
            ) as transaction:
                transaction.set_data("file_size", file_path.stat().st_size)
                transaction.set_data("file_type", file_path.suffix.lower())

            adapter = self.select_adaptor(int(duration_seconds))
            match adapter.adapter_type:
                case AdapterType.SYNCHRONOUS:
                    transcription_job = await adapter.start(audio_file_path_or_recording=file_path)
                case AdapterType.ASYNC:
                    transcription_job = await adapter.start(audio_file_path_or_recording=recording)
                case _:
                    msg = "adapter not recognised"
                    raise RuntimeError(msg)

        if not transcription_job.transcript:
            transcription_job = await self.check_transcription(adapter.name, transcription_job)
        return transcription_job

import logging
import tempfile
from pathlib import Path

import sentry_sdk

from common.audio.ffmpeg import get_duration
from common.convert_american_to_british_spelling import convert_american_to_british_spelling
from common.database.postgres_models import Transcription
from common.services.exceptions import AudioFileTooLongError, TranscriptionFailedError
from common.services.storage_services import get_storage_service
from common.settings import get_settings
from common.types import TranscriptionJobMessageData
from workers.transcription.services._stt import _STT
from workers.transcription.services.azure_stt import AzureSTT
from workers.transcription.services.azure_stt_batch import AzureSTTBatch

logger = logging.getLogger(__name__)

settings = get_settings()

storage_service = get_storage_service(settings.STORAGE_SERVICE_NAME)

# Audio up to 2h uses the synchronous adapter; up to 4h uses the batch adapter;
# anything longer is rejected.
MAX_DURATION_SYNC = 7_200  # seconds (2 hours)
MAX_DURATION_BATCH = 14_400  # seconds (4 hours)

# The two adapters, keyed by their `name`, so an async job can be resumed by name.
_ADAPTERS_BY_NAME: dict[str, type[_STT]] = {
    AzureSTT.name: AzureSTT,
    AzureSTTBatch.name: AzureSTTBatch,
}


class TranscriptionServiceManager:
    """Selects and drives the Azure STT adapter based on audio length.

    Short audio uses the synchronous `AzureSTT`; longer audio uses the
    asynchronous `AzureSTTBatch`. There are only these two adapters, so
    selection is a simple length check.
    """

    def select_stt_service(self, duration_seconds: int) -> type[_STT]:
        if duration_seconds < MAX_DURATION_SYNC:
            return AzureSTT
        if duration_seconds < MAX_DURATION_BATCH:
            return AzureSTTBatch
        msg = f"Audio file is too long for transcription: {duration_seconds:,}s"
        raise AudioFileTooLongError(msg)

    async def perform_transcription_steps(self, transcription: Transcription) -> TranscriptionJobMessageData:
        """Transcribe an already-preprocessed recording (FFmpeg preprocessing done upstream)."""
        recording = transcription.recordings[0]

        with tempfile.TemporaryDirectory() as tempdir:
            temp_file_path = Path(tempdir) / Path(recording.s3_file_key).name
            await storage_service.download(recording.s3_file_key, temp_file_path)

            duration_seconds = get_duration(temp_file_path)

            with sentry_sdk.start_transaction(
                op="process", name="collect_file_metadata_before_transcription"
            ) as transaction:
                transaction.set_data("file_size", temp_file_path.stat().st_size)
                transaction.set_tag("file_ext", temp_file_path.suffix.lower().lstrip("."))

            adapter = self.select_stt_service(int(duration_seconds))
            # The sync adapter transcribes the local file; the batch adapter submits the
            # recording for Azure to fetch. Two adapters, so branch on the class directly.
            if adapter is AzureSTT:
                transcription_job = await adapter.start(audio_file_path_or_recording=temp_file_path)
            else:
                transcription_job = await adapter.start(audio_file_path_or_recording=recording)

        if not transcription_job.transcript:
            transcription_job = await self.check_transcription(adapter.name, transcription_job)
        return transcription_job

    async def check_transcription(
        self, adapter_name: str, async_transcription_message_data: TranscriptionJobMessageData
    ) -> TranscriptionJobMessageData:
        adapter = _ADAPTERS_BY_NAME.get(adapter_name)
        if adapter is None:
            msg = f"Transcription service {adapter_name} is not available"
            raise TranscriptionFailedError(msg)

        transcription_job = await adapter.check(async_transcription_message_data)
        if transcription_job.transcript:
            for entry in transcription_job.transcript:
                entry["text"] = convert_american_to_british_spelling(entry["text"])
        return transcription_job

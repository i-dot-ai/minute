from pathlib import Path
from uuid import uuid4

import pytest

from common.database.postgres_models import Recording
from common.services.transcription_services.aws import AWSTranscribeAdapter
from common.services.transcription_services.azure import AzureSpeechAdapter
from common.services.transcription_services.azure_async import AzureBatchTranscriptionAdapter


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("adapter", "wrong_input", "expected_message"),
    [
        (AzureSpeechAdapter, Recording(user_id=uuid4(), s3_file_key="recording.mp3"), "needs a local audio file"),
        (AWSTranscribeAdapter, Path("recording.mp3"), "needs a Recording"),
        (AzureBatchTranscriptionAdapter, Path("recording.mp3"), "needs a Recording"),
    ],
)
async def test_start_rejects_the_wrong_kind_of_input(adapter, wrong_input, expected_message):
    # TranscriptionServiceManager passes the downloaded file to synchronous adapters and the Recording to async ones.
    with pytest.raises(TypeError, match=expected_message):
        await adapter.start(wrong_input)

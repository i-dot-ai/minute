import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch

import pytest

from common.types import TranscriptionJobMessageData
from workers.transcription.services import AzureSTT, AzureSTTBatch
from workers.transcription.services.transcription_manager import (
    MAX_DURATION_BATCH,
    AudioFileTooLongError,
    TranscriptionServiceManager,
)

MANAGER_MODULE = "workers.transcription.services.transcription_manager"


def _fake_download():
    """Return an async download(key, path) that creates an empty file at `path`.

    `perform_transcription_steps` reads `path.stat().st_size` for telemetry, so the
    downloaded file must actually exist on disk.
    """

    async def _download(key, path):  # noqa: ARG001
        Path(path).write_bytes(b"")

    return _download


@pytest.fixture
def manager():
    return TranscriptionServiceManager()


@pytest.fixture
def mock_recording():
    recording = Mock()
    recording.s3_file_key = "test_file.mp3"
    return recording


@pytest.fixture
def mock_transcription(mock_recording):
    transcription = Mock()
    transcription.recordings = [mock_recording]
    return transcription


class TestSelectSttService:
    """The adapter is chosen purely by audio length: short -> sync, longer -> batch."""

    def test_short_audio_selects_sync(self, manager):
        assert manager.select_stt_service(60) is AzureSTT

    def test_just_under_sync_limit_selects_sync(self, manager):
        assert manager.select_stt_service(7_199) is AzureSTT

    def test_medium_audio_selects_batch(self, manager):
        assert manager.select_stt_service(7_200) is AzureSTTBatch

    def test_just_under_batch_limit_selects_batch(self, manager):
        assert manager.select_stt_service(MAX_DURATION_BATCH - 1) is AzureSTTBatch

    def test_too_long_raises(self, manager):
        with pytest.raises(AudioFileTooLongError, match="too long"):
            manager.select_stt_service(MAX_DURATION_BATCH + 1)


class TestCheckTranscription:
    @pytest.mark.asyncio
    @patch(f"{MANAGER_MODULE}.convert_american_to_british_spelling")
    async def test_check_transcription_success(self, mock_convert, manager):
        mock_convert.return_value = "converted"
        message = TranscriptionJobMessageData(
            transcription_service=AzureSTT.name,
            transcript=[{"text": "color", "speaker": "S1", "start_time": 0.0, "end_time": 1.0}],
        )

        with patch.object(AzureSTT, "check", new=AsyncMock(return_value=message)):
            result = await manager.check_transcription(AzureSTT.name, message)

        assert result.transcript[0]["text"] == "converted"
        mock_convert.assert_called_once_with("color")

    @pytest.mark.asyncio
    async def test_check_transcription_unknown_adapter(self, manager):
        message = TranscriptionJobMessageData(transcription_service="nope", transcript=None)
        with pytest.raises(RuntimeError, match="not available"):
            await manager.check_transcription("nope", message)

    @pytest.mark.asyncio
    async def test_check_transcription_no_transcript_skips_conversion(self, manager):
        message = TranscriptionJobMessageData(transcription_service=AzureSTTBatch.name, transcript=None)
        with patch.object(AzureSTTBatch, "check", new=AsyncMock(return_value=message)):
            result = await manager.check_transcription(AzureSTTBatch.name, message)
        assert result.transcript is None


class TestPerformTranscriptionSteps:
    @pytest.mark.asyncio
    async def test_synchronous_path(self, manager, mock_transcription, mock_recording):
        """Short audio: sync adapter returns a completed job; no check needed."""
        completed = TranscriptionJobMessageData(
            transcription_service=AzureSTT.name,
            transcript=[{"text": "hi", "speaker": "S1", "start_time": 0.0, "end_time": 1.0}],
        )
        download_mock = AsyncMock(side_effect=_fake_download())
        with (
            tempfile.NamedTemporaryFile(suffix=".mp3") as temp_file,
            patch(f"{MANAGER_MODULE}.storage_service.download", new=download_mock) as mock_download,
            patch(f"{MANAGER_MODULE}.get_duration", return_value=1_500),
            patch.object(AzureSTT, "start", new=AsyncMock(return_value=completed)) as mock_start,
        ):
            mock_recording.s3_file_key = temp_file.name

            result = await manager.perform_transcription_steps(mock_transcription)

            assert result.transcript is not None
            mock_start.assert_awaited_once()
            mock_download.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_synchronous_empty_transcript_is_terminal(self, manager, mock_transcription, mock_recording):
        """Sync adapter returning [] (no speech) is complete -- check must NOT run."""
        empty = TranscriptionJobMessageData(transcription_service=AzureSTT.name, transcript=[])
        download_mock = AsyncMock(side_effect=_fake_download())
        with (
            tempfile.NamedTemporaryFile(suffix=".mp3") as temp_file,
            patch(f"{MANAGER_MODULE}.storage_service.download", new=download_mock),
            patch(f"{MANAGER_MODULE}.get_duration", return_value=1_500),
            patch.object(AzureSTT, "start", new=AsyncMock(return_value=empty)),
            patch.object(manager, "check_transcription", new=AsyncMock()) as mock_check,
        ):
            mock_recording.s3_file_key = temp_file.name

            result = await manager.perform_transcription_steps(mock_transcription)

            assert result.transcript == []
            mock_check.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_asynchronous_path_triggers_check(self, manager, mock_transcription, mock_recording):
        """Long audio: batch adapter returns a job with no transcript, so check runs."""
        submitted = TranscriptionJobMessageData(transcription_service=AzureSTTBatch.name, job_name="job-123")
        completed = TranscriptionJobMessageData(
            transcription_service=AzureSTTBatch.name,
            job_name="job-123",
            transcript=[{"text": "hi", "speaker": "S1", "start_time": 0.0, "end_time": 1.0}],
        )
        with (
            tempfile.NamedTemporaryFile(suffix=".mp3") as temp_file,
            patch(f"{MANAGER_MODULE}.storage_service.download", new=AsyncMock(side_effect=_fake_download())),
            patch(f"{MANAGER_MODULE}.get_duration", return_value=10_000),
            patch.object(AzureSTTBatch, "start", new=AsyncMock(return_value=submitted)) as mock_start,
            patch.object(manager, "check_transcription", new=AsyncMock(return_value=completed)) as mock_check,
        ):
            mock_recording.s3_file_key = temp_file.name

            result = await manager.perform_transcription_steps(mock_transcription)

            assert result.transcript is not None
            mock_start.assert_awaited_once_with(audio_file_path_or_recording=mock_recording)
            mock_check.assert_awaited_once()

    def test_adapter_names_are_distinct(self):
        assert AzureSTT.name != AzureSTTBatch.name

"""Unit tests for the audio worker's convert-and-handoff logic.

These mock storage, the database and ffmpeg so they run offline (no MiniStack, no
paid APIs). The full upload -> convert -> transcribe -> minute path is covered by
tests/test_queues_e2e.py.
"""

import uuid
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from audio_worker.audio_service import AudioConversionFailedError, AudioService
from common.types import TaskType, TranscriptionReadyMessageData, WorkerMessage


@pytest.fixture
def queues():
    audio_queue = MagicMock()
    transcription_queue = MagicMock()
    return audio_queue, transcription_queue


@pytest.fixture
def service(queues):
    audio_queue, transcription_queue = queues
    return AudioService(audio_queue_service=audio_queue, transcription_queue_service=transcription_queue)


def _make_recording(s3_file_key: str):
    recording = MagicMock()
    recording.s3_file_key = s3_file_key
    recording.user_id = uuid.uuid4()
    recording.transcription_id = uuid.uuid4()
    return recording


@pytest.mark.asyncio
async def test_process_message_mono_mp3_skips_conversion(service, queues):
    """A mono mp3 needs no conversion: no new Recording, duration handed straight over."""
    audio_queue, transcription_queue = queues
    transcription_id = uuid.uuid4()
    minute_id = uuid.uuid4()
    recording = _make_recording("uploads/original.mp3")

    with (
        patch.object(AudioService, "_load_recording_and_minute", return_value=(recording, minute_id)),
        patch("audio_worker.audio_service.storage_service") as mock_storage,
        patch("audio_worker.audio_service.ffmpeg_utils") as mock_ffmpeg,
        patch("audio_worker.audio_service.SessionLocal") as mock_session_local,
    ):
        mock_storage.download = AsyncMock()
        mock_storage.upload = AsyncMock()
        mock_ffmpeg.get_num_audio_channels.return_value = 1
        mock_ffmpeg.get_duration.return_value = 123.0

        await service.process_message(WorkerMessage(id=transcription_id, type=TaskType.CONVERT))

        mock_ffmpeg.convert_to_mp3.assert_not_called()
        mock_session_local.assert_not_called()  # no new Recording row
        mock_storage.upload.assert_not_awaited()

    transcription_queue.publish_message.assert_called_once()
    published = transcription_queue.publish_message.call_args[0][0]
    assert published.id == minute_id
    assert published.type == TaskType.TRANSCRIPTION
    assert isinstance(published.data, TranscriptionReadyMessageData)
    assert published.data.duration_seconds == 123.0


@pytest.mark.asyncio
async def test_process_message_converts_non_mono(service, queues):
    """A stereo / non-mp3 input is converted and a new Recording row is created."""
    audio_queue, transcription_queue = queues
    transcription_id = uuid.uuid4()
    minute_id = uuid.uuid4()
    recording = _make_recording("uploads/original.wav")

    with (
        patch.object(AudioService, "_load_recording_and_minute", return_value=(recording, minute_id)),
        patch("audio_worker.audio_service.storage_service") as mock_storage,
        patch("audio_worker.audio_service.ffmpeg_utils") as mock_ffmpeg,
        patch("audio_worker.audio_service.SessionLocal") as mock_session_local,
    ):
        mock_storage.download = AsyncMock()
        mock_storage.upload = AsyncMock()
        mock_ffmpeg.get_num_audio_channels.return_value = 2
        mock_ffmpeg.convert_to_mp3.return_value = Path("/tmp/original_converted.mp3")  # noqa: S108
        mock_ffmpeg.get_duration.return_value = 456.0

        session = MagicMock()
        mock_session_local.return_value.__enter__.return_value = session

        await service.process_message(WorkerMessage(id=transcription_id, type=TaskType.CONVERT))

        mock_ffmpeg.convert_to_mp3.assert_called_once()
        mock_storage.upload.assert_awaited_once()
        session.add.assert_called_once()
        session.commit.assert_called_once()

    published = transcription_queue.publish_message.call_args[0][0]
    assert published.id == minute_id
    assert published.data.duration_seconds == 456.0


@pytest.mark.asyncio
async def test_process_message_failure_marks_transcription_failed(service, queues):
    """A conversion failure marks the transcription FAILED and does not hand off."""
    audio_queue, transcription_queue = queues
    transcription_id = uuid.uuid4()
    minute_id = uuid.uuid4()
    recording = _make_recording("uploads/original.wav")

    with (
        patch.object(AudioService, "_load_recording_and_minute", return_value=(recording, minute_id)),
        patch("audio_worker.audio_service.storage_service") as mock_storage,
        patch("audio_worker.audio_service.ffmpeg_utils") as mock_ffmpeg,
        patch.object(AudioService, "_mark_transcription_failed") as mock_mark_failed,
    ):
        mock_storage.download = AsyncMock()
        mock_ffmpeg.get_num_audio_channels.return_value = 2
        mock_ffmpeg.convert_to_mp3.side_effect = RuntimeError("ffmpeg boom")

        with pytest.raises(AudioConversionFailedError):
            await service.process_message(WorkerMessage(id=transcription_id, type=TaskType.CONVERT))

        mock_mark_failed.assert_called_once()
        assert mock_mark_failed.call_args[0][0] == transcription_id

    transcription_queue.publish_message.assert_not_called()

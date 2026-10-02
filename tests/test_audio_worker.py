"""Unit tests for the standalone audio worker."""

import uuid
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from audio_worker.audio_service import AudioConversionFailedError, AudioService
from audio_worker.worker_service import AudioWorker
from common.types import AudioWorkerMessage, TaskType, TranscriptionReadyMessageData


def _message(s3_file_key: str = "uploads/original.mp3") -> AudioWorkerMessage:
    return AudioWorkerMessage(
        user_id=uuid.uuid4(),
        transcription_id=uuid.uuid4(),
        minute_id=uuid.uuid4(),
        s3_file_key=s3_file_key,
    )


@pytest.fixture
def queues():
    audio_queue = MagicMock()
    transcription_queue = MagicMock()
    return audio_queue, transcription_queue


@pytest.fixture
def service(queues):
    audio_queue, transcription_queue = queues
    return AudioService(audio_queue_service=audio_queue, transcription_queue_service=transcription_queue)


@pytest.mark.asyncio
async def test_process_message_mono_mp3_skips_conversion(service, queues):
    _, transcription_queue = queues
    message = _message()

    with (
        patch("audio_worker.audio_service.storage_service") as storage,
        patch("audio_worker.audio_service.ffmpeg_utils") as ffmpeg,
        patch("audio_worker.audio_service.SessionLocal") as session_local,
    ):
        storage.download = AsyncMock()
        storage.upload = AsyncMock()
        ffmpeg.get_num_audio_channels.return_value = 1
        ffmpeg.get_duration.return_value = 123.0

        await service.process_message(message)

    ffmpeg.convert_to_mp3.assert_not_called()
    storage.upload.assert_not_awaited()
    session_local.assert_not_called()
    published = transcription_queue.publish_message.call_args.args[0]
    assert published.id == message.minute_id
    assert published.type == TaskType.TRANSCRIPTION
    assert isinstance(published.data, TranscriptionReadyMessageData)
    assert published.data.duration_seconds == 123.0


@pytest.mark.asyncio
async def test_process_message_converts_and_creates_deterministic_recording(service, queues):
    _, transcription_queue = queues
    message = _message("uploads/original.wav")
    expected_id = uuid.uuid5(uuid.NAMESPACE_URL, f"minute:converted-recording:{message.transcription_id}")

    with (
        patch("audio_worker.audio_service.storage_service") as storage,
        patch("audio_worker.audio_service.ffmpeg_utils") as ffmpeg,
        patch("audio_worker.audio_service.SessionLocal") as session_local,
    ):
        storage.download = AsyncMock()
        storage.upload = AsyncMock()
        ffmpeg.get_num_audio_channels.return_value = 2
        ffmpeg.convert_to_mp3.return_value = Path("/tmp/original_converted.mp3")  # noqa: S108
        ffmpeg.get_duration.return_value = 456.0
        session = MagicMock()
        session_local.return_value.__enter__.return_value = session

        await service.process_message(message)

    storage.upload.assert_awaited_once()
    insert_statement = session.exec.call_args.args[0]
    assert insert_statement.compile().params["id"] == expected_id
    assert transcription_queue.publish_message.call_args.args[0].data.duration_seconds == 456.0


@pytest.mark.asyncio
async def test_database_failure_removes_uploaded_conversion(service):
    message = _message("uploads/original.wav")
    with (
        patch("audio_worker.audio_service.storage_service") as storage,
        patch("audio_worker.audio_service.ffmpeg_utils.get_num_audio_channels", return_value=2),
        patch(
            "audio_worker.audio_service.ffmpeg_utils.convert_to_mp3",
            return_value=Path("/tmp/original_converted.mp3"),  # noqa: S108
        ),
        patch("audio_worker.audio_service.ffmpeg_utils.get_duration", return_value=10.0),
        patch("audio_worker.audio_service.SessionLocal") as session_local,
    ):
        storage.download = AsyncMock()
        storage.upload = AsyncMock()
        storage.delete = AsyncMock()
        session = MagicMock()
        session.commit.side_effect = RuntimeError("database unavailable")
        session_local.return_value.__enter__.return_value = session

        with pytest.raises(RuntimeError, match="database unavailable"):
            await service.process_message(message)

    storage.delete.assert_awaited_once()


@pytest.mark.asyncio
async def test_invalid_media_marks_transcription_failed(service, queues):
    _, transcription_queue = queues
    message = _message("uploads/original.wav")
    with (
        patch("audio_worker.audio_service.storage_service") as storage,
        patch("audio_worker.audio_service.ffmpeg_utils.get_num_audio_channels") as channels,
        patch("audio_worker.audio_service.ffmpeg_utils.convert_to_mp3", side_effect=RuntimeError("invalid audio")),
        patch.object(AudioService, "_mark_transcription_failed", return_value=True) as mark_failed,
        patch("audio_worker.audio_service.capture_event"),
    ):
        storage.download = AsyncMock()
        channels.return_value = 2
        with pytest.raises(AudioConversionFailedError) as exc_info:
            await service.process_message(message)

    assert exc_info.value.marked_failed is True
    mark_failed.assert_called_once_with(message.transcription_id, str(exc_info.value))
    transcription_queue.publish_message.assert_not_called()


@pytest.mark.asyncio
async def test_transient_handoff_failure_is_retried(service, queues):
    _, transcription_queue = queues
    message = _message()
    transcription_queue.publish_message.side_effect = RuntimeError("queue unavailable")
    with (
        patch("audio_worker.audio_service.storage_service") as storage,
        patch("audio_worker.audio_service.ffmpeg_utils") as ffmpeg,
        patch.object(AudioService, "_mark_transcription_failed") as mark_failed,
    ):
        storage.download = AsyncMock()
        ffmpeg.get_num_audio_channels.return_value = 1
        ffmpeg.get_duration.return_value = 10.0
        with pytest.raises(RuntimeError, match="queue unavailable"):
            await service.process_message(message)

    mark_failed.assert_not_called()


@pytest.fixture
def worker(tmp_path, queues):
    audio_queue, transcription_queue = queues
    with patch("audio_worker.worker_service.SignalHandler"):
        audio_worker = AudioWorker(
            audio_queue_service=audio_queue,
            transcription_queue_service=transcription_queue,
            heartbeat_path=tmp_path / "audio_worker_main.heartbeat",
        )
        audio_worker.signal_handler.signal_received = False
        yield audio_worker


@pytest.mark.asyncio
async def test_worker_completes_message_on_success(worker, queues):
    audio_queue, _ = queues
    with patch.object(worker.audio_service, "process_message", AsyncMock()):
        await worker.handle_message(_message(), "receipt")
    audio_queue.complete_message.assert_called_once_with("receipt")


@pytest.mark.asyncio
async def test_worker_completes_terminal_media_failure(worker, queues):
    audio_queue, _ = queues
    error = AudioConversionFailedError("invalid audio", marked_failed=True)
    with patch.object(worker.audio_service, "process_message", AsyncMock(side_effect=error)):
        await worker.handle_message(_message(), "receipt")
    audio_queue.complete_message.assert_called_once_with("receipt")


@pytest.mark.asyncio
async def test_worker_retries_transient_failure_after_current_lease(worker, queues):
    audio_queue, _ = queues
    with patch.object(worker.audio_service, "process_message", AsyncMock(side_effect=RuntimeError("S3 down"))):
        await worker.handle_message(_message(), "receipt")
    audio_queue.abandon_message.assert_not_called()
    audio_queue.complete_message.assert_not_called()


@pytest.mark.asyncio
async def test_worker_abandons_message_received_during_shutdown(worker, queues):
    audio_queue, _ = queues
    audio_queue.receive_message.return_value = [(_message(), "receipt")]
    worker.signal_handler.signal_received = True
    with patch.object(worker.audio_service, "process_message", AsyncMock()) as process:
        await worker.poll_once()
    process.assert_not_awaited()
    audio_queue.abandon_message.assert_called_once_with("receipt")


def test_heartbeat_touches_file(worker):
    worker.heartbeat_path.unlink()
    worker.beat()
    assert worker.heartbeat_path.exists()

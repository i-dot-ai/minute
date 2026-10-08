"""Unit tests for the standalone audio worker."""

import uuid
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from tenacity import retry, stop_after_attempt, wait_none

from audio_worker import handler
from common.types import AudioWorkerMessage, TaskType, TranscriptionReadyMessageData


def _message(s3_file_key: str = "uploads/original.mp3") -> AudioWorkerMessage:
    return AudioWorkerMessage(
        user_id=uuid.uuid4(),
        transcription_id=uuid.uuid4(),
        minute_id=uuid.uuid4(),
        s3_file_key=s3_file_key,
        run_id=uuid.uuid4(),
    )


retry_without_wait = retry(stop=stop_after_attempt(4), wait=wait_none(), reraise=True)


@pytest.mark.asyncio
async def test_mono_mp3_hands_off_once_with_run_id() -> None:
    message = _message()
    input_queue = MagicMock()
    output_queue = MagicMock()
    storage = MagicMock(download=AsyncMock())

    with patch("audio_worker.handler.ffmpeg") as ffmpeg:
        ffmpeg.get_num_channels.return_value = 1
        ffmpeg.get_duration.return_value = 10.0
        await handler.handle_message(message, "receipt", input_queue, output_queue, storage)

    ffmpeg.convert_to_mp3.assert_not_called()
    published = output_queue.publish_message.call_args.kwargs["message"]
    assert published.id == message.minute_id
    assert published.type == TaskType.TRANSCRIPTION
    assert isinstance(published.data, TranscriptionReadyMessageData)
    assert published.data.duration_seconds == 10.0
    assert published.run_id == message.run_id
    input_queue.complete_message.assert_called_once_with("receipt")


@pytest.mark.asyncio
async def test_conversion_hands_off_with_run_id() -> None:
    message = _message("uploads/original.wav")
    input_queue = MagicMock()
    output_queue = MagicMock()
    storage = MagicMock(download=AsyncMock(), upload=AsyncMock())

    with (
        patch("audio_worker.handler.ffmpeg") as ffmpeg,
        patch("audio_worker.handler.repository.add_recording") as add_recording,
    ):
        ffmpeg.get_num_channels.return_value = 2
        ffmpeg.get_duration.return_value = 20.0
        ffmpeg.convert_to_mp3.return_value = Path("converted.mp3")
        await handler.handle_message(message, "receipt", input_queue, output_queue, storage)

    add_recording.assert_called_once()
    published = output_queue.publish_message.call_args.kwargs["message"]
    assert published.data.duration_seconds == 20.0
    assert published.run_id == message.run_id
    input_queue.complete_message.assert_called_once_with("receipt")


@pytest.mark.asyncio
async def test_download_failure_marks_failed_and_deadletters() -> None:
    message = _message()
    input_queue = MagicMock()
    output_queue = MagicMock()
    storage = MagicMock(download=AsyncMock(side_effect=RuntimeError("storage unavailable")))

    with (
        patch("audio_worker.handler.retry_four_times", retry_without_wait),
        patch("audio_worker.handler.repository.mark_transcription_failed", return_value=True) as mark_failed,
        patch("audio_worker.handler.capture_event") as capture,
    ):
        await handler.handle_message(message, "receipt", input_queue, output_queue, storage)

    assert storage.download.await_count == 4
    mark_failed.assert_called_once()
    capture.assert_called_once()
    input_queue.deadletter_message.assert_called_once_with(message, "receipt")
    input_queue.abandon_message.assert_not_called()
    input_queue.complete_message.assert_not_called()
    output_queue.publish_message.assert_not_called()


@pytest.mark.asyncio
async def test_download_transient_failure_succeeds_on_fourth_attempt() -> None:
    message = _message()
    input_queue = MagicMock()
    output_queue = MagicMock()
    storage = MagicMock(
        download=AsyncMock(side_effect=[RuntimeError("one"), RuntimeError("two"), RuntimeError("three"), None])
    )

    with (
        patch("audio_worker.handler.retry_four_times", retry_without_wait),
        patch("audio_worker.handler.ffmpeg") as ffmpeg,
        patch("audio_worker.handler.repository.mark_transcription_failed") as mark_failed,
    ):
        ffmpeg.get_num_channels.return_value = 1
        ffmpeg.get_duration.return_value = 10.0
        await handler.handle_message(message, "receipt", input_queue, output_queue, storage)

    assert storage.download.await_count == 4
    mark_failed.assert_not_called()
    output_queue.publish_message.assert_called_once()
    input_queue.complete_message.assert_called_once_with("receipt")


@pytest.mark.asyncio
async def test_publish_failure_retries_then_marks_failed_and_deadletters() -> None:
    message = _message()
    input_queue = MagicMock()
    output_queue = MagicMock()
    output_queue.publish_message.side_effect = RuntimeError("queue unavailable")
    storage = MagicMock(download=AsyncMock())

    with (
        patch("audio_worker.handler.retry_four_times", retry_without_wait),
        patch("audio_worker.handler.ffmpeg") as ffmpeg,
        patch("audio_worker.handler.repository.mark_transcription_failed", return_value=True) as mark_failed,
    ):
        ffmpeg.get_num_channels.return_value = 1
        ffmpeg.get_duration.return_value = 10.0
        await handler.handle_message(message, "receipt", input_queue, output_queue, storage)

    assert output_queue.publish_message.call_count == 4
    mark_failed.assert_called_once()
    input_queue.deadletter_message.assert_called_once_with(message, "receipt")
    input_queue.complete_message.assert_not_called()


@pytest.mark.asyncio
async def test_completion_failure_after_publish_is_not_terminal() -> None:
    message = _message()
    input_queue = MagicMock()
    input_queue.complete_message.side_effect = RuntimeError("delete failed")
    output_queue = MagicMock()
    storage = MagicMock(download=AsyncMock())

    with (
        patch("audio_worker.handler.retry_four_times", retry_without_wait),
        patch("audio_worker.handler.ffmpeg") as ffmpeg,
        patch("audio_worker.handler.repository.mark_transcription_failed") as mark_failed,
    ):
        ffmpeg.get_num_channels.return_value = 1
        ffmpeg.get_duration.return_value = 10.0
        await handler.handle_message(message, "receipt", input_queue, output_queue, storage)

    output_queue.publish_message.assert_called_once()
    assert input_queue.complete_message.call_count == 4
    mark_failed.assert_not_called()
    input_queue.deadletter_message.assert_not_called()


@pytest.mark.asyncio
async def test_status_failure_leaves_message_for_sqs_redelivery() -> None:
    message = _message()
    input_queue = MagicMock()
    output_queue = MagicMock()
    storage = MagicMock(download=AsyncMock(side_effect=RuntimeError("storage unavailable")))

    with (
        patch("audio_worker.handler.retry_four_times", retry_without_wait),
        patch(
            "audio_worker.handler.repository.mark_transcription_failed",
            side_effect=RuntimeError("database unavailable"),
        ),
        pytest.raises(RuntimeError, match="database unavailable"),
    ):
        await handler.handle_message(message, "receipt", input_queue, output_queue, storage)

    input_queue.deadletter_message.assert_not_called()
    input_queue.complete_message.assert_not_called()


@pytest.mark.asyncio
async def test_deadletter_failure_is_raised_for_sqs_redelivery() -> None:
    message = _message()
    input_queue = MagicMock()
    input_queue.deadletter_message.side_effect = RuntimeError("DLQ unavailable")
    output_queue = MagicMock()
    storage = MagicMock(download=AsyncMock(side_effect=RuntimeError("storage unavailable")))

    with (
        patch("audio_worker.handler.retry_four_times", retry_without_wait),
        patch("audio_worker.handler.repository.mark_transcription_failed", return_value=True),
        pytest.raises(RuntimeError, match="DLQ unavailable"),
    ):
        await handler.handle_message(message, "receipt", input_queue, output_queue, storage)

    assert input_queue.deadletter_message.call_count == 4

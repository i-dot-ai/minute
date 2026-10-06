import tempfile
import uuid
from collections.abc import Callable
from pathlib import Path

from tenacity import retry as retry_
from tenacity import stop_after_attempt, wait_exponential

from audio_worker import ffmpeg, repository
from common.services.posthog_client import capture_event
from common.services.queue_services.base import QueueService
from common.services.storage_services.base import StorageService
from common.settings import get_structured_logger
from common.types import AudioWorkerMessage, TaskType, TranscriptionReadyMessageData, WorkerMessage

slogger = get_structured_logger()


retry_four_times = retry_(
    stop=stop_after_attempt(4),  # 1 + 3 retries
    wait=wait_exponential(multiplier=1, min=1, max=4),
    reraise=True,
)


def retry(function: Callable, /, *args, **kwargs):
    return retry_four_times(function)(*args, **kwargs)


async def handle_message(
    message: AudioWorkerMessage,
    receipt_handle: str,
    input_queue: QueueService[AudioWorkerMessage],
    output_queue: QueueService[WorkerMessage],
    storage_service: StorageService,
) -> None:
    slogger.refresh_context()
    slogger.set_context_field("user_id", str(message.user_id))
    slogger.set_context_field("transcription_id", str(message.transcription_id))
    slogger.set_context_field("minute_id", str(message.minute_id))

    with tempfile.TemporaryDirectory() as tempdir:
        audio_path = Path(tempdir) / Path(message.s3_file_key).name
        try:
            await retry(storage_service.download, key=message.s3_file_key, path=audio_path)
        except Exception as exc:
            slogger.exception("Failed to download audio file from storage", exc=exc)
            _fail_message(message, receipt_handle, input_queue, "download", exc)
            return

        try:
            num_channels = retry(ffmpeg.get_num_channels, input_path=audio_path, timeout=60)
            duration = retry(ffmpeg.get_duration, input_path=audio_path, timeout=60)
        except Exception as exc:
            slogger.exception("Failed to get audio file info", exc=exc)
            _fail_message(message, receipt_handle, input_queue, "probe", exc)
            return

        if Path(message.s3_file_key).suffix.lower() == ".mp3" and num_channels == 1:
            _hand_over_message(message, receipt_handle, duration, input_queue, output_queue)
            return

        mp3_audio_path = audio_path.with_name(f"{audio_path.stem}_converted.mp3")
        try:
            retry(ffmpeg.convert_to_mp3, input_path=audio_path, output_path=mp3_audio_path, timeout=15 * 60)
        except Exception as exc:
            slogger.exception("Failed to convert audio to MP3", exc=exc)
            _fail_message(message, receipt_handle, input_queue, "conversion", exc)
            return

        new_recording_id = uuid.uuid5(uuid.NAMESPACE_URL, f"minute:converted-recording:{message.transcription_id}")
        new_s3_file_key = str(Path(message.s3_file_key).with_name(f"{new_recording_id}.mp3"))
        try:
            await retry(storage_service.upload, key=new_s3_file_key, path=mp3_audio_path)
        except Exception as exc:
            slogger.exception("Failed to upload converted file to storage", exc=exc)
            _fail_message(message, receipt_handle, input_queue, "upload", exc)
            return

    try:
        repository.add_recording(
            user_id=message.user_id,
            transcription_id=message.transcription_id,
            recording_id=new_recording_id,
            s3_file_key=new_s3_file_key,
        )
    except Exception as exc:
        slogger.exception("Failed to add recording to database", exc=exc)
        _fail_message(message, receipt_handle, input_queue, "database", exc)
        return

    _hand_over_message(message, receipt_handle, duration, input_queue, output_queue)


def _hand_over_message(
    message: AudioWorkerMessage,
    receipt_handle: str,
    duration: float,
    input_queue: QueueService[AudioWorkerMessage],
    output_queue: QueueService[WorkerMessage],
) -> None:
    worker_message = WorkerMessage(
        id=message.minute_id,
        type=TaskType.TRANSCRIPTION,
        data=TranscriptionReadyMessageData(duration_seconds=duration),
        run_id=message.run_id,
    )
    try:
        retry(output_queue.publish_message, message=worker_message)
    except Exception as exc:
        slogger.exception("Failed to publish transcription message")
        _fail_message(message, receipt_handle, input_queue, "handoff", exc)
        return

    try:
        retry(input_queue.complete_message, receipt_handle)
    except Exception:
        slogger.exception("Published transcription message but failed to complete audio message")


def _fail_message(
    message: AudioWorkerMessage,
    receipt_handle: str,
    input_queue: QueueService[AudioWorkerMessage],
    stage: str,
    exc: Exception,
) -> None:
    error = f"Audio processing failed during {stage}: {exc!s}"
    changed = repository.mark_transcription_failed(
        transcription_id=message.transcription_id,
        minute_id=message.minute_id,
        run_id=message.run_id,
        error=error,
    )

    if changed:
        capture_event(
            distinct_id=message.user_id,
            event="transcription_failed",
            properties={
                "transcriptionId": str(message.transcription_id),
                "stage": stage,
                "runId": str(message.run_id) if message.run_id else None,
            },
        )
    retry(input_queue.deadletter_message, message, receipt_handle)

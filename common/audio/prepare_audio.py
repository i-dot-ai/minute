"""Download the newest recording and, if needed, convert it to a mono mp3 for STT.

Same behaviour as the old TranscriptionServiceManager.perform_transcription_steps /
get_recording_to_process (chore/idempotency-refactor's worker/actions/prepare_audio.py),
on the ported storage and repository.
"""

import asyncio
import uuid
from collections.abc import Callable
from contextlib import AbstractAsyncContextManager
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from sqlalchemy.ext.asyncio import async_sessionmaker

from common.audio.ffmpeg import convert_to_mp3, get_duration, get_num_audio_channels
from common.database.postgres_models import Recording, Transcription
from common.database.repository import add_recording
from common.services.storage.s3 import download, upload
from common.settings import get_structured_logger

slogger = get_structured_logger()
SUPPORTED_FORMATS = {".mp3"}

# ponytail: idempotency relies on processing always using the NEWEST recording
# (transcription.recordings[0], ordered created_datetime desc): on retry the newest row is
# the converted mp3, so conversion is skipped. A concurrent dual-run may still insert a
# duplicate converted recording (benign). Add a (transcription_id, kind) unique index if seen.


@dataclass(frozen=True)
class PreparedAudio:
    recording: Recording  # the mono mp3 STT should use (the upload, or the converted copy)
    file_path: Path
    duration_seconds: float


def is_ready_for_stt(recording: Recording, num_channels: int) -> bool:
    return Path(recording.s3_file_key).suffix.lower() in SUPPORTED_FORMATS and num_channels == 1


async def prepare_audio(
    transcription: Transcription,
    work_dir: Path,
    storage: Callable[[], AbstractAsyncContextManager[Any]],
    db: async_sessionmaker,
) -> PreparedAudio:
    """`work_dir` is owned by the caller and holds the prepared file when this returns.

    `storage` is the S3 client factory and `db` the sessionmaker, both from the caller's
    Runtime: this helper reads no globals.
    """
    recording = transcription.recordings[0]
    temp_file_path = work_dir / Path(recording.s3_file_key).name
    async with storage() as s3:
        await download(s3, recording.s3_file_key, temp_file_path)

        num_channels = await asyncio.to_thread(get_num_audio_channels, temp_file_path)
        if is_ready_for_stt(recording, num_channels):
            slogger.info("Recording is already a mono mp3, no conversion needed")
            duration = await asyncio.to_thread(get_duration, temp_file_path)
            return PreparedAudio(recording=recording, file_path=temp_file_path, duration_seconds=duration)

        slogger.info("Recording is not a mono mp3, converting")
        mp3_path = await asyncio.to_thread(convert_to_mp3, temp_file_path)
        new_recording_id = uuid.uuid4()
        new_s3_key = str(Path(recording.s3_file_key).with_name(f"{new_recording_id}.mp3"))
        await upload(s3, new_s3_key, mp3_path)
    async with db() as session:
        converted = await add_recording(
            session,
            recording_id=new_recording_id,
            s3_file_key=new_s3_key,
            user_id=recording.user_id,
            transcription_id=recording.transcription_id,
        )
        await session.commit()
    duration = await asyncio.to_thread(get_duration, mp3_path)
    return PreparedAudio(recording=converted, file_path=mp3_path, duration_seconds=duration)

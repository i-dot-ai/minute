"""Action: download the recording, convert to mono mp3 when needed, persist the converted file."""

import asyncio
import subprocess
import uuid
from dataclasses import dataclass
from pathlib import Path

import ffmpeg

from common.database.postgres_database import async_engine
from common.database.postgres_models import Recording, Transcription
from common.services.storage_services import get_storage_service
from common.settings import get_settings, get_structured_logger

slogger = get_structured_logger()
settings = get_settings()
storage_service = get_storage_service(settings.STORAGE_SERVICE_NAME)
SUPPORTED_FORMATS = {".mp3"}

# ponytail: idempotency of this action relies on processing always using the NEWEST
# recording (transcription.recordings[0], ordered created_datetime desc): on resume the
# newest row is the converted mp3, so conversion is skipped. A concurrent dual-run may
# still insert a duplicate converted recording (benign: second runner reuses the first's
# file). If duplicates are ever observed, add a (transcription_id, kind) partial unique index.


@dataclass(frozen=True)
class PreparedAudio:
    recording: Recording
    file_path: Path
    duration_seconds: float


def _convert_to_mp3(input_file_path: Path) -> Path:
    if not Path(input_file_path).is_file():
        msg = f"Input file not found: {input_file_path}"
        slogger.error("{msg}", msg=msg)
        raise FileNotFoundError(msg)

    output_file = input_file_path.with_name(f"{input_file_path.stem}_converted.mp3")
    try:
        probe = ffmpeg.probe(input_file_path)
        audio_streams = [stream for stream in probe["streams"] if stream["codec_type"] == "audio"]

        if not audio_streams:
            msg = f"No audio stream found in the input file: {input_file_path}"
            slogger.error("{msg}", msg=msg)
            raise RuntimeError(msg)

        input_stream = ffmpeg.input(input_file_path)
        output_args = {
            "acodec": "libmp3lame",  # Use LAME MP3 encoder
            "loglevel": "warning",  # Show warnings and errors
            "audio_bitrate": "192k",
            "ac": 1,
        }
        output_stream = ffmpeg.output(input_stream, output_file.as_posix(), **output_args)
        ffmpeg.run(output_stream, overwrite_output=True)
    except Exception:
        slogger.exception("MP3 conversion failed")
        raise
    else:
        return output_file


def _num_audio_channels(file_path: Path) -> int:
    try:
        result = subprocess.run(  # noqa: S603
            [  # noqa: S607
                "ffprobe",
                "-v",
                "error",
                "-select_streams",
                "a:0",
                "-show_entries",
                "stream=channels",
                "-of",
                "default=noprint_wrappers=1:nokey=1",
                str(file_path),
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode != 0:
            msg = f"ffprobe command failed with return code {result.returncode}. ffprobe stderr: {result.stderr}"
            slogger.error("{msg}", msg=msg)
            return 2
        return int(result.stdout.strip())
    except Exception:
        slogger.exception("Failed to get number of audio channels, assuming stereo")
        return 2


def _duration(file_path: Path) -> float:
    try:
        result = subprocess.run(  # noqa: S603
            [  # noqa: S607
                "ffprobe",
                "-v",
                "error",
                "-select_streams",
                "a:0",
                "-show_entries",
                "stream=duration",
                "-of",
                "default=noprint_wrappers=1:nokey=1",
                str(file_path),
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode != 0:
            msg = f"ffprobe command failed with return code {result.returncode},ffprobe stderr: {result.stderr}"
            slogger.error("{msg}", msg=msg)
            return 14400.0
        return float(result.stdout.strip())
    except Exception:
        slogger.exception("Failed to get audio duration, assuming max")
        return 14400.0


async def prepare_audio(transcription: Transcription, work_dir: Path) -> PreparedAudio:
    """Download and, if needed, convert the newest recording for transcription.

    `work_dir` is owned by the caller (the workflow holds the TemporaryDirectory open
    for the whole transcription phase, because the STT call needs the file afterwards).
    """
    # recordings are ordered created_datetime desc, so [0] is the newest: either the
    # user's upload or (on resume) a previously converted mp3.
    recording = transcription.recordings[0]
    file_extension = Path(recording.s3_file_key).suffix.lower()
    temp_file_path = work_dir / Path(recording.s3_file_key).name
    await storage_service.download(recording.s3_file_key, temp_file_path)

    num_channels = await asyncio.to_thread(_num_audio_channels, temp_file_path)
    if file_extension in SUPPORTED_FORMATS and num_channels == 1:
        slogger.info("Recording is already a mono mp3, no conversion needed")
        duration = await asyncio.to_thread(_duration, temp_file_path)
        return PreparedAudio(recording=recording, file_path=temp_file_path, duration_seconds=duration)

    slogger.info("Recording is not a mono mp3, converting")
    mp3_path = await asyncio.to_thread(_convert_to_mp3, temp_file_path)
    new_recording_id = uuid.uuid4()
    new_s3_key = str(Path(recording.s3_file_key).with_name(f"{new_recording_id}.mp3"))
    await storage_service.upload(new_s3_key, mp3_path)
    from sqlmodel.ext.asyncio.session import AsyncSession

    async with AsyncSession(async_engine) as session:
        session.add(
            Recording(
                id=new_recording_id,
                s3_file_key=new_s3_key,
                user_id=recording.user_id,
                transcription_id=recording.transcription_id,
            )
        )
        await session.commit()
    duration = await asyncio.to_thread(_duration, mp3_path)
    return PreparedAudio(recording=recording, file_path=mp3_path, duration_seconds=duration)

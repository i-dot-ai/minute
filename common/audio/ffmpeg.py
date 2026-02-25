import logging
import subprocess
from pathlib import Path

import ffmpeg

from common.constants import MONO_CHANNELS, SUPPORTED_FORMATS

logger = logging.getLogger(__name__)


def convert_to_mp3(input_file_path: Path, output_path: Path | None = None) -> Path:
    """
    Converts audio to mono MP3 format, preserving the input sample rate.

    Args:
        input_file_path: Path to input audio file
        output_path: Optional output path. If None, creates path with _converted suffix
    """
    if not Path(input_file_path).is_file():
        msg = f"Input file not found: {input_file_path}"
        logger.error(msg)
        raise FileNotFoundError(msg)

    if output_path is None:
        output_path = input_file_path.with_name(f"{input_file_path.stem}_converted.mp3")

    output_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        logger.info("Probing input file for audio streams")
        probe = ffmpeg.probe(input_file_path)
        audio_streams = [stream for stream in probe["streams"] if stream["codec_type"] == "audio"]

        if not audio_streams:
            msg = f"No audio stream found in the input file: {input_file_path}"
            logger.error(msg)
            raise RuntimeError(msg)

        input_stream = ffmpeg.input(input_file_path)

        output_args = {
            "acodec": "libmp3lame",
            "loglevel": "warning",
            "audio_bitrate": "192k",
            "ac": MONO_CHANNELS,
        }

        output_stream = ffmpeg.output(input_stream, str(output_path), **output_args)
        ffmpeg.run(output_stream, overwrite_output=True)
        logger.info("FFmpeg command completed successfully")

    except Exception:
        logger.exception("Unexpected error occurred in MP3 conversion")
        raise
    else:
        return output_path


def get_num_audio_channels(file_path: Path) -> int:
    try:
        logger.info("Getting number of audio stream using ffprobe")
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
            logger.error(msg)
            return 2
        raw_channels = result.stdout.strip()
        channels = int(raw_channels)
        msg = f"Successfully got number of channels using ffprobe: {channels=}"
        logger.info(msg)
        return channels

    except Exception:
        msg = "Failed to get number of channels"
        logger.exception(msg)
        return 2


def is_audio_ready_for_transcription(file_path: Path, file_extension: str) -> bool:
    """
    Checks if an audio file is ready for transcription without conversion.
    Returns True if the file is in a supported format and is mono.
    """
    if file_extension not in SUPPORTED_FORMATS:
        return False
    num_channels = get_num_audio_channels(file_path)
    return num_channels == MONO_CHANNELS


def get_duration(file_path: Path) -> float:
    try:
        logger.info("Getting audio duration using ffprobe")
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
            logger.error(msg)
            return 2
        raw_duration = result.stdout.strip()
        duration = float(raw_duration)
        msg = f"Successfully got duration using ffprobe: {duration=}"
        logger.info(msg)
        return duration

    except Exception as e:
        msg = f"Failed to get duration: {e!s}"
        logger.exception(msg)
        return 14400.0

import subprocess
from pathlib import Path

import ffmpeg

from common.settings import get_structured_logger

slogger = get_structured_logger()


def convert_to_mp3(input_file_path: Path) -> Path:
    if not Path(input_file_path).is_file():
        msg = f"Input file not found: {input_file_path}"
        slogger.error("Input file not found: {input_file_path}", input_file_path=str(input_file_path))
        raise FileNotFoundError(msg)

    output_file = input_file_path.with_name(f"{input_file_path.stem}_converted.mp3")
    try:
        slogger.info("Probing input file for audio streams")
        probe = ffmpeg.probe(input_file_path)
        audio_streams = [stream for stream in probe["streams"] if stream["codec_type"] == "audio"]

        if not audio_streams:
            msg = f"No audio stream found in the input file: {input_file_path}"
            slogger.error(
                "No audio stream found in the input file: {input_file_path}",
                input_file_path=str(input_file_path),
            )
            raise RuntimeError(msg)

        # Open the input file
        input_stream = ffmpeg.input(input_file_path)

        # Set up the output stream with the desired parameters
        output_args = {
            "acodec": "libmp3lame",  # Use LAME MP3 encoder
            "loglevel": "warning",  # Show warnings and errors
            "audio_bitrate": "192k",
            "ac": 1,
        }

        output_stream = ffmpeg.output(input_stream, output_file.as_posix(), **output_args)

        # Run the FFmpeg command
        ffmpeg.run(output_stream, overwrite_output=True)
        slogger.info("FFmpeg command completed successfully")

    except Exception:
        slogger.exception("Unexpected error occurred in MP3 conversion")
        raise
    else:
        return output_file


def get_num_audio_channels(file_path: Path) -> int:
    try:
        slogger.info("Getting number of audio stream using ffprobe")
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
            slogger.error(
                "ffprobe command failed with return code {returncode}. ffprobe stderr: {stderr}",
                returncode=str(result.returncode),
                stderr=result.stderr,
            )
            return 2
        channels = result.stdout.strip()
        channels = int(channels)
        slogger.info("Successfully got number of channels using ffprobe: {channels}", channels=str(channels))
        return channels

    except Exception:
        slogger.exception("Failed to get number of channels")
        return 2


def get_duration(file_path: Path) -> float:
    try:
        slogger.info("Getting audio duration using ffprobe")
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
            slogger.error(
                "ffprobe command failed with return code {returncode}, ffprobe stderr: {stderr}",
                returncode=str(result.returncode),
                stderr=result.stderr,
            )
            return 2
        duration = result.stdout.strip()
        duration = float(duration)
        slogger.info("Successfully got duration using ffprobe: {duration}", duration=str(duration))
        return duration

    except Exception:
        slogger.exception("Failed to get duration")
        return 14400.0

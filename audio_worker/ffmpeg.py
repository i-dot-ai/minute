import subprocess
from pathlib import Path


def convert_to_mp3(input_path: Path, output_path: Path, timeout: int) -> Path:
    """Convert to mp3."""

    if not Path(input_path).is_file():
        msg = f"Input file not found: {input_path}"
        raise FileNotFoundError(msg)

    try:
        subprocess.run(  # noqa: S603
            [  # noqa: S607
                "ffmpeg",
                "-i",
                str(input_path),
                "-acodec",
                "libmp3lame",
                "-b:a",
                "192k",
                "-ac",
                "1",
                "-loglevel",
                "warning",
                "-y",
                str(output_path),
            ],
            check=True,
            timeout=timeout,
        )
        return output_path

    except Exception as exc:
        msg = f"Failed to convert to mp3 {input_path}: {exc!s}"
        raise RuntimeError(msg) from exc


def get_num_channels(input_path: Path, timeout: int) -> int:
    """Get number of channels."""

    if not Path(input_path).is_file():
        msg = f"Input file not found: {input_path}"
        raise FileNotFoundError(msg)

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
                str(input_path),
            ],
            capture_output=True,
            timeout=timeout,
            check=True,
            text=True,
        )

        return int(result.stdout.strip())

    except Exception as exc:
        msg = f"Failed to get number of channels {input_path}: {exc!s}"
        raise RuntimeError(msg) from exc


def get_duration(input_path: Path, timeout: int) -> float:
    """Get duration."""

    if not Path(input_path).is_file():
        msg = f"Input file not found: {input_path}"
        raise FileNotFoundError(msg)

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
                str(input_path),
            ],
            capture_output=True,
            timeout=timeout,
            check=True,
            text=True,
        )

        return float(result.stdout.strip())

    except Exception as exc:
        msg = f"Failed to get duration {input_path}: {exc!s}"
        raise RuntimeError(msg) from exc

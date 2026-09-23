import logging
import subprocess
from pathlib import Path

logger = logging.getLogger(__name__)


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
        duration = result.stdout.strip()
        duration = float(duration)
        msg = f"Successfully got duration using ffprobe: {duration=}"
        logger.info(msg)
        return duration

    except Exception as e:
        msg = f"Failed to get duration: {e!s}"
        logger.exception(msg)
        return 14400.0

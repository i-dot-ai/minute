import logging
import tempfile
from pathlib import Path
from typing import cast

import numpy
import soundfile
from common.audio.ffmpeg import convert_to_mp3

from evals.transcription.src.core.ami.selection import MeetingSegment

logger = logging.getLogger(__name__)


class CachePaths:
    """
    Container for cached audio and transcript file paths.
    """

    def __init__(self, audio_path: Path, transcript_path: Path):
        """
        Initializes cache paths for audio and transcript files.
        """
        self.audio = audio_path
        self.transcript = transcript_path

    def is_complete(self) -> bool:
        """
        Checks if both audio and transcript files exist in the cache.
        """
        return self.audio.exists() and self.transcript.exists()


def get_cache_paths(processed_dir: Path, segment: MeetingSegment, index: int) -> CachePaths:
    """
    Using the given path, meeting segment, and index, returns the expected cache paths for
    the audio file and transcript.
    """
    audio_path = processed_dir / f"{segment.meeting_id}_{index:06d}.mp3"
    transcript_path = audio_path.with_suffix(".txt")
    return CachePaths(audio_path, transcript_path)


def load_audio(path: Path) -> numpy.ndarray:
    """
    Loads the audio from the given path and returns it as a numpy array.
    """
    audio, _sample_rate = soundfile.read(path)
    return cast(numpy.ndarray, audio)


def save_audio(path: Path, audio: numpy.ndarray, sample_rate: int) -> None:
    """
    Saves the given audio array to the specified path as mono MP3 (preserves sample rate).
    """
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_file:
        temp_path = Path(temp_file.name)
        soundfile.write(temp_path, audio, sample_rate, subtype="PCM_16")

    try:
        convert_to_mp3(temp_path, path)
    finally:
        temp_path.unlink(missing_ok=True)


def load_transcript(path: Path) -> str:
    """
    Loads the transcript text from the given path and returns it as a string.
    """
    return path.read_text(encoding="utf-8")


def save_transcript(path: Path, text: str) -> None:
    """
    Saves the given transcript text to the specified path.
    """
    path.write_text(text, encoding="utf-8")

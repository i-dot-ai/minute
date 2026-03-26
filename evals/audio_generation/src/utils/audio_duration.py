import io

from pydub import AudioSegment


def get_audio_duration(audio_bytes: bytes) -> float:
    """
    Returns duration in seconds for mp3 bytes.
    """
    audio = AudioSegment.from_mp3(io.BytesIO(audio_bytes))
    return len(audio) / 1000.0

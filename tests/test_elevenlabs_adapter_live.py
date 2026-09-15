"""Transcribe real audio with the live ElevenLabs Scribe API.

Needs ELEVENLABS_API_KEY in .env, issued for the stack ELEVENLABS_BASE_URL points at (the EU data residency
stack unless overridden). Every other stack rejects the key with a 401.
"""

import re
from pathlib import Path

import ffmpeg
import pytest

from common.audio.ffmpeg import convert_to_mp3, get_duration
from common.services.transcription_services.elevenlabs import ElevenLabsSpeechAdapter
from tests.marks import costs_money, requires_audio_data
from tests.utils import FileTypeTests

pytestmark = [costs_money, requires_audio_data]

# Long enough for a few speaker turns, short enough to keep each run cheap.
CLIP_SECONDS = 60


@pytest.fixture
def audio_clip(tmp_path) -> Path:
    """Trim the first normal fixture and convert it to mp3, as the manager does before calling the adapter."""
    source = sorted(Path(".data").joinpath("test_audio").joinpath(FileTypeTests.NORMAL).iterdir())[0]
    clip = tmp_path / f"clip{source.suffix}"
    ffmpeg.run(
        ffmpeg.output(ffmpeg.input(source, t=CLIP_SECONDS), clip.as_posix(), c="copy"),
        overwrite_output=True,
        quiet=True,
    )
    return convert_to_mp3(clip)


@pytest.mark.asyncio
async def test_transcribes_a_clip_into_speaker_turns(audio_clip):
    assert ElevenLabsSpeechAdapter.is_available(), "Set ELEVENLABS_API_KEY in .env to run this test"

    result = await ElevenLabsSpeechAdapter.start(audio_clip)

    assert result.transcription_service == ElevenLabsSpeechAdapter.name
    assert result.transcript, "ElevenLabs returned no dialogue entries"
    clip_duration = get_duration(audio_clip)
    for entry in result.transcript:
        assert re.fullmatch(r"speaker_\d+", entry["speaker"]), entry
        assert entry["text"].strip(), entry
        assert 0 <= entry["start_time"] <= entry["end_time"] <= clip_duration + 1, entry

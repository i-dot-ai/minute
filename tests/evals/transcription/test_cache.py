from __future__ import annotations

import numpy as np

from evals.transcription.src.core.ami.cache import (
    CachePaths,
    get_cache_paths,
    load_audio,
    load_transcript,
    save_audio,
    save_transcript,
)
from evals.transcription.src.models import MeetingSegment


def test_cache_paths_is_complete_returns_true_when_both_exist(tmp_path):
    audio_path = tmp_path / "audio.mp3"
    transcript_path = tmp_path / "transcript.txt"
    audio_path.write_bytes(b"audio")
    transcript_path.write_bytes(b"text")

    cache_paths = CachePaths(audio_path, transcript_path)

    assert cache_paths.is_complete() is True


def test_cache_paths_is_complete_returns_false_when_audio_missing(tmp_path):
    audio_path = tmp_path / "audio.mp3"
    transcript_path = tmp_path / "transcript.txt"
    transcript_path.write_bytes(b"text")

    cache_paths = CachePaths(audio_path, transcript_path)

    assert cache_paths.is_complete() is False


def test_cache_paths_is_complete_returns_false_when_transcript_missing(tmp_path):
    audio_path = tmp_path / "audio.mp3"
    transcript_path = tmp_path / "transcript.txt"
    audio_path.write_bytes(b"audio")

    cache_paths = CachePaths(audio_path, transcript_path)

    assert cache_paths.is_complete() is False


def test_get_cache_paths_returns_expected_paths(tmp_path):
    segment = MeetingSegment(meeting_id="ES2008a", utterance_cutoff_time=None)

    cache_paths = get_cache_paths(tmp_path, segment, 5)

    assert cache_paths.audio == tmp_path / "ES2008a_000005.mp3"
    assert cache_paths.transcript == tmp_path / "ES2008a_000005.txt"


def test_load_audio_returns_numpy_array(tmp_path):
    import soundfile as sf

    audio_path = tmp_path / "test.wav"
    expected_audio = np.array([0.1, 0.2, 0.3], dtype=np.float32)
    sf.write(audio_path, expected_audio, 16000)

    loaded_audio = load_audio(audio_path)

    assert isinstance(loaded_audio, np.ndarray)
    assert len(loaded_audio) == len(expected_audio)
    np.testing.assert_allclose(loaded_audio, expected_audio, rtol=1e-3, atol=1e-4)


def test_save_audio_creates_mp3_file(tmp_path, monkeypatch):
    audio_data = np.array([0.1, 0.2, 0.3], dtype=np.float32)
    output_path = tmp_path / "output.mp3"

    def fake_convert(_input_path, output_path):
        output_path.write_bytes(b"fake mp3 data")

    monkeypatch.setattr("evals.transcription.src.core.ami.cache.convert_to_mp3", fake_convert)

    save_audio(output_path, audio_data, 16000)

    assert output_path.exists()


def test_load_transcript_returns_text(tmp_path):
    transcript_path = tmp_path / "transcript.txt"
    expected_text = "hello world"
    transcript_path.write_text(expected_text, encoding="utf-8")

    loaded_text = load_transcript(transcript_path)

    assert loaded_text == expected_text


def test_save_transcript_writes_text(tmp_path):
    transcript_path = tmp_path / "transcript.txt"
    text = "test transcript"

    save_transcript(transcript_path, text)

    assert transcript_path.read_text(encoding="utf-8") == text

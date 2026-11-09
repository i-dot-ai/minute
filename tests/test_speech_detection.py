"""Speech detection on real audio: ffmpeg generates the silent and non-speech inputs."""

import subprocess
from io import BytesIO
from pathlib import Path
from unittest.mock import Mock

import numpy as np
import pytest

from common.audio import speech_detection
from common.audio.speech_detection import SpeechCheckTier, detect_speech

SAMPLE_MEETING = Path(__file__).resolve().parents[1] / "frontend/tests/fixtures/sample-meeting.mp3"


def _generate(path: Path, *args: str) -> Path:
    """Generates an audio fixture using FFmpeg.

    Args:
        path: Destination path for the audio file.
        *args: FFmpeg input and processing arguments.

    Returns:
        The path to the generated audio file.

    Raises:
        subprocess.CalledProcessError: FFmpeg fails to generate the fixture.
    """
    subprocess.run(["ffmpeg", "-y", "-v", "error", *args, str(path)], check=True)  # noqa: S603, S607
    return path


@pytest.fixture
def silence(tmp_path):
    """Returns a two-minute recording of digital silence."""
    return _generate(tmp_path / "silence.mp3", "-f", "lavfi", "-i", "anullsrc=r=44100:cl=mono", "-t", "120")


@pytest.fixture
def quiet_noise(tmp_path):
    """Returns audible pink noise for testing the VAD tier."""
    return _generate(tmp_path / "noise.mp3", "-f", "lavfi", "-i", "anoisesrc=d=120:c=pink:a=0.02")


@pytest.fixture
def tone(tmp_path):
    """Returns a steady tone with no speech."""
    return _generate(tmp_path / "tone.mp3", "-f", "lavfi", "-i", "sine=f=440:d=30")


@pytest.fixture
def late_speech(tmp_path):
    """Returns a meeting recording preceded by two minutes of silence."""
    return _generate(
        tmp_path / "late.mp3",
        *("-i", str(SAMPLE_MEETING), "-f", "lavfi", "-i", "anullsrc=r=44100:cl=mono"),
        *("-filter_complex", "[1]atrim=0:120[s];[s][0]concat=n=2:v=0:a=1"),
    )


def test_speech_is_detected():
    """Verifies that meeting audio passes the VAD check."""
    check = detect_speech(SAMPLE_MEETING)
    assert check.has_speech
    assert check.tier == SpeechCheckTier.VAD


def test_speech_after_a_long_silence_is_detected(late_speech):
    """Verifies that detection scans beyond a long silent introduction."""
    assert detect_speech(late_speech).has_speech


def test_silence_is_caught_by_the_volume_check_without_running_vad(silence, monkeypatch):
    """Verifies that digital silence bypasses model inference."""
    count_speech = Mock(side_effect=AssertionError)
    monkeypatch.setattr(speech_detection, "count_speech_seconds", count_speech)
    check = detect_speech(silence)
    assert not check.has_speech
    assert check.tier == SpeechCheckTier.VOLUME
    count_speech.assert_not_called()


@pytest.mark.parametrize("fixture", ["quiet_noise", "tone"])
def test_audible_non_speech_is_caught_by_vad(request, fixture):
    """Verifies that audible noise and tones are rejected by VAD."""
    check = detect_speech(request.getfixturevalue(fixture))
    assert not check.has_speech
    assert check.tier == SpeechCheckTier.VAD


def test_vad_stops_once_enough_speech_is_found():
    """Verifies early stopping and optional full-recording processing."""
    assert speech_detection.count_speech_seconds(SAMPLE_MEETING) < 2
    assert speech_detection.count_speech_seconds(SAMPLE_MEETING, stop_after_seconds=float("inf")) > 60


def test_undecodable_audio_raises(tmp_path):
    """Verifies that invalid audio produces an error rather than a silent verdict."""
    bad = tmp_path / "bad.mp3"
    bad.write_bytes(b"not audio")
    with pytest.raises(subprocess.CalledProcessError):
        detect_speech(bad)
    with pytest.raises(RuntimeError):
        speech_detection.count_speech_seconds(bad)


def test_counter_discards_short_runs_and_preserves_confirmed_speech():
    """Verifies that only qualifying runs contribute to the speech duration."""
    counter = speech_detection.SpeechCounter()
    for _ in range(7):
        counter.update(0.9)
    assert counter.speech_seconds == 0
    counter.update(0.0)
    for _ in range(8):
        counter.update(0.9)
    assert counter.speech_seconds == pytest.approx(0.256)
    counter.update(0.0)
    assert counter.speech_seconds == pytest.approx(0.256)


def test_counter_uses_lower_threshold_only_after_speech_starts():
    """Verifies that borderline scores continue speech but cannot start it."""
    counter = speech_detection.SpeechCounter()
    for _ in range(8):
        counter.update(0.4)
    assert counter.speech_seconds == 0
    counter.update(0.9)
    for _ in range(7):
        counter.update(0.4)
    assert counter.speech_seconds == pytest.approx(0.256)


def test_model_instances_keep_recording_state_separate(monkeypatch):
    """Verifies that shared model weights do not share recurrent recording state."""
    state = np.ones((2, 1, 128), dtype=np.float32)
    session = Mock()
    session.run.return_value = (np.array([[0.9]], dtype=np.float32), state)
    monkeypatch.setattr(speech_detection, "_get_model_session", Mock(return_value=session))
    first = speech_detection.SileroModel()
    second = speech_detection.SileroModel()
    window = np.ones(speech_detection.WINDOW_SAMPLES, dtype=np.float32)

    assert first.predict(window) == pytest.approx(0.9)
    first.predict(window)
    second.predict(window)

    initial, continued, independent = [call.args[1] for call in session.run.call_args_list]
    assert not initial["state"].any()
    assert continued["state"].all()
    assert not independent["state"].any()
    assert not independent["input"][0, : speech_detection.CONTEXT_SAMPLES].any()


def test_decoder_cleans_up_after_early_stopping(monkeypatch):
    """Verifies that an unfinished decoder is terminated when its context exits."""
    process = Mock()
    process.stdout = BytesIO(np.ones(speech_detection.WINDOW_SAMPLES * 2, dtype=np.float32).tobytes())
    process.poll.return_value = None
    monkeypatch.setattr(speech_detection.subprocess, "Popen", Mock(return_value=process))

    with speech_detection.decoded_audio_windows(Path("audio.mp3")) as windows:
        assert len(next(windows)) == speech_detection.WINDOW_SAMPLES

    process.kill.assert_called_once()
    process.wait.assert_called_once()
    assert process.stdout.closed


def test_decoder_pads_the_final_window(monkeypatch):
    """Verifies that short final windows are zero-padded to the model input size."""
    process = Mock()
    process.stdout = BytesIO(np.ones(10, dtype=np.float32).tobytes())
    process.wait.return_value = 0
    process.poll.return_value = 0
    monkeypatch.setattr(speech_detection.subprocess, "Popen", Mock(return_value=process))

    with speech_detection.decoded_audio_windows(Path("audio.mp3")) as windows:
        decoded = list(windows)

    assert len(decoded) == 1
    assert len(decoded[0]) == speech_detection.WINDOW_SAMPLES
    assert decoded[0][:10].all()
    assert not decoded[0][10:].any()
    process.kill.assert_not_called()

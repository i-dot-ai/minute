"""Real Silero inference on decoded samples, plus mocked FFmpeg boundary checks.

These tests need no FFmpeg executable; MP3 decoding/resampling is not covered.
"""

import subprocess
import wave
from contextlib import contextmanager
from io import BytesIO
from pathlib import Path
from unittest.mock import Mock

import numpy as np
import pytest

from common.audio import speech_detection
from common.audio.speech_detection import SpeechCheckResult, detect_speech

SAMPLE_SPEECH = Path(__file__).resolve().parents[1] / "frontend/tests/fixtures/sample-speech.wav"


@pytest.fixture
def speech_samples():
    """Four seconds from sample-meeting.mp3, decoded once to mono 16 kHz PCM.

    Regenerate locally with: ffmpeg -i frontend/tests/fixtures/sample-meeting.mp3
    -t 4 -ac 1 -ar 16000 -c:a pcm_s16le frontend/tests/fixtures/sample-speech.wav
    """
    with wave.open(str(SAMPLE_SPEECH), "rb") as recording:
        assert recording.getnchannels() == 1
        assert recording.getframerate() == speech_detection.SAMPLE_RATE
        assert recording.getsampwidth() == 2
        return np.frombuffer(recording.readframes(recording.getnframes()), dtype="<i2").astype(np.float32) / 32768


def _contains_decoded_speech(monkeypatch, samples):
    """Replace only decoding; exercise real windowing, Silero inference and thresholding."""

    @contextmanager
    def decoded_windows(_path):
        yield speech_detection._iter_audio_windows(BytesIO(samples.astype(np.float32).tobytes()))  # noqa: SLF001

    monkeypatch.setattr(speech_detection, "decoded_audio_windows", decoded_windows)
    return speech_detection.contains_speech(Path("decoded-audio.wav"))


def test_speech_is_detected(monkeypatch, speech_samples):
    """Verifies that real speech passes the real VAD model."""
    assert _contains_decoded_speech(monkeypatch, speech_samples)


def test_speech_after_a_long_silence_is_detected(monkeypatch, speech_samples):
    """Verifies that detection scans beyond a long silent introduction."""
    silence = np.zeros(speech_detection.SAMPLE_RATE * 120, dtype=np.float32)
    assert _contains_decoded_speech(monkeypatch, np.concatenate([silence, speech_samples]))


def test_silence_is_caught_by_the_volume_check_without_running_vad(monkeypatch):
    """Verifies that a silent volume result bypasses model inference."""
    monkeypatch.setattr(speech_detection, "get_max_volume_db", Mock(return_value=-91.0))
    contains_speech = Mock(side_effect=AssertionError)
    monkeypatch.setattr(speech_detection, "contains_speech", contains_speech)
    check = detect_speech(Path("silent.mp3"))
    assert not check.has_speech
    assert check.result == SpeechCheckResult.VOLUME
    contains_speech.assert_not_called()


@pytest.mark.parametrize("audio", ["silence", "noise", "tone"])
def test_non_speech_is_caught_by_real_vad(monkeypatch, audio):
    """Verifies that deterministic non-speech samples are rejected by the real model."""
    size = speech_detection.SAMPLE_RATE * 4
    if audio == "noise":
        samples = np.random.default_rng(0).normal(0, 0.02, size)
    elif audio == "tone":
        samples = 0.1 * np.sin(2 * np.pi * 440 * np.arange(size) / speech_detection.SAMPLE_RATE)
    else:
        samples = np.zeros(size, dtype=np.float32)
    assert not _contains_decoded_speech(monkeypatch, samples)


@pytest.mark.parametrize(
    ("probabilities", "expected", "processed_windows"),
    [
        ([0.5, 0.0], True, 1),
        ([0.4, 0.5, 0.0], True, 2),
        ([0.0, 0.4, 0.49], False, 3),
        ([], False, 0),
    ],
)
def test_vad_detects_any_speech_without_a_minimum_duration(monkeypatch, probabilities, expected, processed_windows):
    """Verifies threshold detection and immediate stopping, even for one window."""
    detector = Mock()
    detector.predict.side_effect = probabilities
    monkeypatch.setattr(speech_detection, "SileroModel", Mock(return_value=detector))

    @contextmanager
    def decoded_windows(_path):
        yield iter([np.zeros(speech_detection.WINDOW_SAMPLES, dtype=np.float32) for _ in probabilities])

    monkeypatch.setattr(speech_detection, "decoded_audio_windows", decoded_windows)
    assert speech_detection.contains_speech(Path("audio.mp3")) is expected
    assert detector.predict.call_count == processed_windows


def test_undecodable_audio_raises(monkeypatch):
    """Verifies that decoder failures propagate rather than becoming silent verdicts."""
    bad = Path("bad.mp3")
    monkeypatch.setattr(
        speech_detection.subprocess, "run", Mock(side_effect=subprocess.CalledProcessError(1, "ffmpeg"))
    )
    with pytest.raises(subprocess.CalledProcessError):
        detect_speech(bad)
    process = Mock()
    process.stdout = BytesIO()
    process.wait.return_value = 1
    process.poll.return_value = 1
    monkeypatch.setattr(speech_detection.subprocess, "Popen", Mock(return_value=process))
    with pytest.raises(RuntimeError):
        speech_detection.contains_speech(bad)


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

"""Never publish the old four-hour fallback as an actual measured duration."""

import subprocess
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from common.audio import ffmpeg


def test_sample_audio_has_measured_duration():
    sample = Path(__file__).resolve().parents[1] / "frontend/tests/fixtures/sample-meeting.mp3"
    assert ffmpeg.get_duration(sample) == pytest.approx(98.45, abs=0.1)


@pytest.mark.parametrize("output", ["98.5\n", "N/A\n98.5\n"])
def test_duration_uses_stream_or_container_metadata(monkeypatch, output):
    probe = Mock(return_value=SimpleNamespace(stdout=output))
    monkeypatch.setattr(ffmpeg.subprocess, "run", probe)
    assert ffmpeg.get_duration(Path("audio.mp3")) == 98.5


@pytest.mark.parametrize("output", ["N/A\n", "", "nan\n", "inf\n", "-1\n", "0\n", "bad\n"])
def test_unknown_or_invalid_duration_fails_instead_of_inventing_a_value(monkeypatch, output):
    monkeypatch.setattr(ffmpeg.subprocess, "run", Mock(return_value=SimpleNamespace(stdout=output)))
    with pytest.raises(ValueError, match="Audio duration|could not convert"):
        ffmpeg.get_duration(Path("audio.mp3"))


def test_probe_failure_is_not_hidden(tmp_path):
    with pytest.raises(subprocess.CalledProcessError):
        ffmpeg.get_duration(tmp_path / "missing.mp3")

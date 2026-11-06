"""Measure valid audio; warn and use four hours when duration cannot be determined."""

import shutil
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from common.audio import ffmpeg


@pytest.mark.skipif(shutil.which("ffprobe") is None, reason="Real audio duration check requires ffprobe")
def test_sample_audio_has_measured_duration():
    sample = Path(__file__).resolve().parents[1] / "frontend/tests/fixtures/sample-meeting.mp3"
    assert ffmpeg.get_duration(sample) == pytest.approx(98.45, abs=0.1)


@pytest.mark.parametrize("output", ["98.5\n", "N/A\n98.5\n"])
def test_duration_uses_stream_or_container_metadata(monkeypatch, output):
    probe = Mock(return_value=SimpleNamespace(stdout=output))
    monkeypatch.setattr(ffmpeg.subprocess, "run", probe)
    assert ffmpeg.get_duration(Path("audio.mp3")) == 98.5


@pytest.mark.parametrize("output", ["N/A\n", "", "nan\n", "inf\n", "-1\n", "0\n", "bad\n"])
def test_unknown_or_invalid_duration_defaults_to_four_hours_with_warning(monkeypatch, caplog, output):
    monkeypatch.setattr(ffmpeg.subprocess, "run", Mock(return_value=SimpleNamespace(stdout=output)))
    assert ffmpeg.get_duration(Path("audio.mp3")) == 14400.0
    assert any(record.levelname == "WARNING" and "defaulting to 4 hours" in record.message for record in caplog.records)


def test_probe_failure_defaults_to_four_hours_with_warning(tmp_path, caplog):
    assert ffmpeg.get_duration(tmp_path / "missing.mp3") == 14400.0
    assert any(record.levelname == "WARNING" and "defaulting to 4 hours" in record.message for record in caplog.records)

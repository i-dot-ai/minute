from __future__ import annotations

from unittest.mock import Mock

import numpy as np
import pytest

from evals.transcription.src.core.dataset import prepare_audio_for_transcription
from evals.transcription.src.models import AudioSample, DatasetItem


def test_prepare_audio_for_transcription_uses_cached_path(tmp_path, monkeypatch):
    cached = tmp_path / "cached.wav"
    cached.write_bytes(b"RIFFfake")

    example = DatasetItem(
        audio=AudioSample(path=str(cached), array=np.array([0.0]), sampling_rate=16000),
        text="test",
    )

    mock_ffmpeg = Mock()

    monkeypatch.setattr("ffmpeg.input", mock_ffmpeg)
    monkeypatch.setattr("ffmpeg.output", mock_ffmpeg)
    monkeypatch.setattr("ffmpeg.run", mock_ffmpeg)

    assert prepare_audio_for_transcription(example, 0) == str(cached)

    mock_ffmpeg.assert_not_called()


def test_prepare_audio_for_transcription_downmixes_stereo_and_returns_path(tmp_path, monkeypatch):
    audio_dir = tmp_path / "audio"
    audio_dir.mkdir()
    monkeypatch.setattr("evals.transcription.src.core.dataset.AUDIO_DIR", audio_dir)

    samples = np.array([[0.0, 1.0], [1.0, 0.0]])

    captured = {}

    def fake_write(path, data, sr, subtype=None):  # noqa: ARG001
        captured["data"] = data

    monkeypatch.setattr("evals.transcription.src.core.dataset.soundfile.write", fake_write)
    monkeypatch.setattr("evals.transcription.src.core.dataset.convert_to_mp3", lambda _input, output: output)

    example = DatasetItem(audio=AudioSample(array=samples, sampling_rate=16000, path=""), text="test")
    output_path = prepare_audio_for_transcription(example, 1)

    assert output_path == str(audio_dir / "sample_000001.mp3")
    np.testing.assert_allclose(captured["data"], samples)


def test_prepare_audio_for_transcription_cleans_temp_on_ffmpeg_error(tmp_path, monkeypatch):
    audio_dir = tmp_path / "audio"
    audio_dir.mkdir()
    monkeypatch.setattr("evals.transcription.src.core.dataset.AUDIO_DIR", audio_dir)

    temp_path_holder = {}

    def fake_write(path, data, sr, subtype=None):  # noqa: ARG001
        temp_path_holder["path"] = path

    def fake_run(*_args, **_kwargs):
        msg = "ffmpeg failure"
        raise RuntimeError(msg)

    def fake_convert_to_mp3_error(_input_path, _output_path):
        msg = "ffmpeg failure"
        raise RuntimeError(msg)

    monkeypatch.setattr("evals.transcription.src.core.dataset.soundfile.write", fake_write)
    monkeypatch.setattr("evals.transcription.src.core.dataset.convert_to_mp3", fake_convert_to_mp3_error)

    example = DatasetItem(audio=AudioSample(array=np.zeros((2, 2)), sampling_rate=16000, path=""), text="test")

    with pytest.raises(RuntimeError):
        prepare_audio_for_transcription(example, 2)

    temp_path = temp_path_holder["path"]
    assert temp_path is not None
    assert not temp_path.exists()

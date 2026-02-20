from __future__ import annotations

from unittest.mock import Mock

import numpy as np
import pytest

from evals.transcription.src.core.dataset import prepare_audio_for_transcription


def test_prepare_audio_for_transcription_uses_cached_path(tmp_path, monkeypatch):
    cached = tmp_path / "cached.wav"
    cached.write_bytes(b"RIFFfake")

    example = {"audio": {"path": str(cached), "array": Mock(), "sampling_rate": 16000}}

    def _fail(*_args, **_kwargs):
        msg = "ffmpeg should not be invoked when cached path exists"
        raise AssertionError(msg)

    monkeypatch.setattr("ffmpeg.input", _fail)
    monkeypatch.setattr("ffmpeg.output", _fail)
    monkeypatch.setattr("ffmpeg.run", _fail)

    assert prepare_audio_for_transcription(example, 0) == str(cached)


def test_prepare_audio_for_transcription_downmixes_stereo_and_returns_path(tmp_path, monkeypatch):
    audio_dir = tmp_path / "audio"
    audio_dir.mkdir()
    monkeypatch.setattr("evals.transcription.src.core.dataset.AUDIO_DIR", audio_dir)

    samples = np.array([[0.0, 1.0], [1.0, 0.0]])

    captured = {}

    def fake_write(path, data, sr, subtype=None):  # noqa: ARG001
        captured["data"] = data

    def fake_convert_to_mp3(_input_path, output_path):
        return output_path

    monkeypatch.setattr("evals.transcription.src.core.dataset.soundfile.write", fake_write)
    monkeypatch.setattr("evals.transcription.src.core.dataset.convert_to_mp3", fake_convert_to_mp3)

    example = {"audio": {"array": samples, "sampling_rate": 16000}}
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

    example = {"audio": {"array": np.zeros((2, 2)), "sampling_rate": 16000}}

    with pytest.raises(RuntimeError):
        prepare_audio_for_transcription(example, 2)

    temp_path = temp_path_holder["path"]
    assert temp_path is not None
    assert not temp_path.exists()

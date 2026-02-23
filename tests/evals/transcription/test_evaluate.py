from __future__ import annotations

from unittest.mock import MagicMock, patch

from evals.transcription.src.evaluate import run_evaluation


def test_run_evaluation_with_num_samples(tmp_path, monkeypatch):
    monkeypatch.setattr("evals.transcription.src.evaluate.WORKDIR", tmp_path)

    mock_dataset = MagicMock()
    mock_dataset.__len__ = MagicMock(return_value=10)
    mock_dataset.__getitem__ = MagicMock(return_value=MagicMock(text="test", audio=MagicMock(path="/fake/path.wav")))

    with (
        patch("evals.transcription.src.evaluate.load_benchmark_dataset", return_value=mock_dataset),
        patch("evals.transcription.src.evaluate.run_engines_parallel", return_value=[]),
        patch("evals.transcription.src.evaluate.save_results"),
        patch(
            "evals.transcription.src.evaluate.prepare_audio_for_transcription",
            return_value="/fake/prepared.wav",
        ),
        patch("evals.transcription.src.evaluate.get_duration", return_value=1.0),
    ):
        result = run_evaluation(num_samples=5)

        assert result is None


def test_run_evaluation_with_sample_duration_fraction(tmp_path, monkeypatch):
    monkeypatch.setattr("evals.transcription.src.evaluate.WORKDIR", tmp_path)

    mock_dataset = MagicMock()
    mock_dataset.__len__ = MagicMock(return_value=10)
    mock_dataset.__getitem__ = MagicMock(return_value=MagicMock(text="test", audio=MagicMock(path="/fake/path.wav")))

    with (
        patch("evals.transcription.src.evaluate.load_benchmark_dataset", return_value=mock_dataset),
        patch("evals.transcription.src.evaluate.run_engines_parallel", return_value=[]),
        patch("evals.transcription.src.evaluate.save_results"),
        patch(
            "evals.transcription.src.evaluate.prepare_audio_for_transcription",
            return_value="/fake/prepared.wav",
        ),
        patch("evals.transcription.src.evaluate.get_duration", return_value=1.0),
    ):
        result = run_evaluation(sample_duration_fraction=0.5)

        assert result is None


def test_run_evaluation_default_parameters(tmp_path, monkeypatch):
    monkeypatch.setattr("evals.transcription.src.evaluate.WORKDIR", tmp_path)

    mock_dataset = MagicMock()
    mock_dataset.__len__ = MagicMock(return_value=2)
    mock_dataset.__getitem__ = MagicMock(return_value=MagicMock(text="test", audio=MagicMock(path="/fake/path.wav")))

    with (
        patch("evals.transcription.src.evaluate.load_benchmark_dataset", return_value=mock_dataset),
        patch("evals.transcription.src.evaluate.run_engines_parallel", return_value=[]),
        patch("evals.transcription.src.evaluate.save_results"),
        patch(
            "evals.transcription.src.evaluate.prepare_audio_for_transcription",
            return_value="/fake/prepared.wav",
        ),
        patch("evals.transcription.src.evaluate.get_duration", return_value=1.0),
    ):
        result = run_evaluation()

        assert result is None

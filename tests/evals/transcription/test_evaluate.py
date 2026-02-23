from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from evals.transcription.src.evaluate import run_evaluation


@pytest.mark.parametrize(
    ("kwargs", "dataset_len", "expected_load_call"),
    [
        ({"num_samples": 5}, 10, {"num_samples": 5, "sample_duration_fraction": None}),
        ({"sample_duration_fraction": 0.5}, 10, {"num_samples": None, "sample_duration_fraction": 0.5}),
        ({}, 2, {"num_samples": None, "sample_duration_fraction": None}),
    ],
)
def test_run_evaluation(tmp_path, monkeypatch, kwargs, dataset_len, expected_load_call):
    monkeypatch.setattr("evals.transcription.src.evaluate.WORKDIR", tmp_path)

    mock_dataset = MagicMock()
    mock_dataset.__len__ = MagicMock(return_value=dataset_len)
    mock_dataset.__getitem__ = MagicMock(return_value=MagicMock(text="test", audio=MagicMock(path="/fake/path.wav")))

    with (
        patch("evals.transcription.src.evaluate.load_benchmark_dataset", return_value=mock_dataset) as mock_load,
        patch("evals.transcription.src.evaluate.run_engines_parallel", return_value=[]) as mock_run,
        patch("evals.transcription.src.evaluate.save_results") as mock_save,
        patch(
            "evals.transcription.src.evaluate.prepare_audio_for_transcription",
            return_value="/fake/prepared.wav",
        ),
        patch("evals.transcription.src.evaluate.get_duration", return_value=1.0),
    ):
        result = run_evaluation(**kwargs)

        assert result is None
        mock_load.assert_called_once_with(**expected_load_call)
        mock_run.assert_called_once()
        assert len(mock_run.call_args.kwargs["adapters_config"]) == 2
        assert mock_run.call_args.kwargs["indices"] == list(range(dataset_len))
        mock_save.assert_called_once()

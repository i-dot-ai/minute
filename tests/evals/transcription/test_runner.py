from __future__ import annotations

import pytest

from evals.transcription.src.core.runner import run_engines_parallel
from tests.evals.transcription.conftest import FakeAdapter, FakeDataset


def test_run_engines_parallel_bookkeeping(tmp_path):
    wav_a = tmp_path / "a.wav"
    wav_b = tmp_path / "b.wav"
    wav_a.write_bytes(b"RIFFfake")
    wav_b.write_bytes(b"RIFFfake")

    dataset = FakeDataset(
        [
            {"text": "hello world", "audio": {"path": str(wav_a)}},
            {"text": "good night", "audio": {"path": str(wav_b)}},
        ]
    )

    adapters_config = [{"adapter": FakeAdapter("A", "hello world", proc_sec=0.5), "label": "Adapter A"}]

    results = run_engines_parallel(
        adapters_config=adapters_config,
        indices=[0, 1],
        dataset=dataset,
        wav_write_fn=lambda ex, _idx: ex.audio.path,
        duration_fn=lambda _path: 2.0,
    )

    assert len(results) == 1
    summary = results[0].summary
    expected_summary = {
        "engine": "A",
        "num_samples": 2,
    }
    actual_summary = {
        "engine": summary.engine,
        "num_samples": summary.num_samples,
    }
    assert expected_summary == actual_summary
    assert summary.process_sec == pytest.approx(1.0)
    assert summary.audio_sec == pytest.approx(4.0)
    assert summary.processing_speed_ratio == pytest.approx(0.25)

    samples_out = results[0].samples
    expected_samples = {
        "dataset_index_0": 0,
        "dataset_index_1": 1,
        "engine": "A",
    }
    actual_samples = {
        "dataset_index_0": samples_out[0].dataset_index,
        "dataset_index_1": samples_out[1].dataset_index,
        "engine": samples_out[0].engine,
    }
    assert expected_samples == actual_samples
    assert samples_out[0].processing_speed_ratio == pytest.approx(0.25)

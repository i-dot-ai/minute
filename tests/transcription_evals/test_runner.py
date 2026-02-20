from __future__ import annotations

import pytest

from evals.transcription.src.core.runner import run_engines_parallel
from tests.transcription_evals.conftest import FakeAdapter, FakeDataset


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

    adapters_config = [FakeAdapter("A", "hello world", proc_sec=0.5)]

    results = run_engines_parallel(
        adapters_config=adapters_config,
        indices=[0, 1],
        dataset=dataset,
        wav_write_fn=lambda ex, _idx: ex["audio"]["path"],
        duration_fn=lambda _path: 2.0,
    )

    assert len(results) == 1
    summary = results[0]["summary"]
    assert summary["engine"] == "A"
    assert summary["process_sec"] == pytest.approx(1.0)
    assert summary["processing_speed_ratio"] == pytest.approx(0.25)

    samples_out = results[0]["samples"]
    assert samples_out[0]["dataset_index"] == 0
    assert samples_out[1]["dataset_index"] == 1
    assert samples_out[0]["engine"] == "A"
    assert samples_out[0]["processing_speed_ratio"] == pytest.approx(0.25)

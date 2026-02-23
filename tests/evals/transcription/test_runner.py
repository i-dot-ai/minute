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

    adapters_config = [FakeAdapter("A", "hello world", proc_sec=0.5)]

    results = run_engines_parallel(
        adapters_config=adapters_config,
        indices=[0, 1],
        dataset=dataset,
        wav_write_fn=lambda ex, _idx: ex.audio.path,
        duration_fn=lambda _path: 2.0,
        run_id="test_run",
        timestamp="20240101_120000",
    )

    assert len(results) == 1

    summary = results[0].summary.model_dump()
    expected_summary = {
        "engine": "A",
        "num_samples": 2,
        "process_sec": 1.0,
        "audio_sec": 4.0,
        "processing_speed_ratio": 0.25,
    }
    for key, value in expected_summary.items():
        if isinstance(value, float):
            assert summary[key] == pytest.approx(value)
        else:
            assert summary[key] == value

    samples = results[0].samples
    assert samples[0].dataset_index == 0
    assert samples[1].dataset_index == 1
    assert samples[0].engine == "A"
    assert samples[0].processing_speed_ratio == pytest.approx(0.25)

from __future__ import annotations

import pytest

from evals.transcription.src.core.runner import (
    _compute_all_metrics,
    _extract_segments,
    _validate_and_convert_diarization,
    run_engines_parallel,
)
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
        adapters=adapters_config,
        indices=[0, 1],
        dataset=dataset,
        wav_write_fn=lambda ex, _idx: ex.audio.path,
        duration_fn=lambda _path: 2.0,
        run_id="test_run",
        timestamp="20240101_120000",
        dataset_version="FakeDataset_v0",
        dataset_split="test",
    )

    assert len(results) == 1

    summary = results[0].summary.model_dump()
    expected_summary = {
        "run_id": "test_run",
        "timestamp": "20240101_120000",
        "dataset_version": "FakeDataset_v0",
        "engine_version": "A",
        "split": "test",
        "n_examples": 2,
    }
    for key, value in expected_summary.items():
        if isinstance(value, float):
            assert summary[key] == pytest.approx(value)
        else:
            assert summary[key] == value

    samples = results[0].samples
    assert samples[0].example_id == "0"
    assert samples[1].example_id == "1"
    assert samples[0].engine_version == "A"
    assert samples[0].metrics["processing_speed_ratio"] == pytest.approx(0.25)


@pytest.mark.parametrize(
    ("result_attr", "example_attr", "expected_dialogue", "expected_reference"),
    [
        (
            {"dialogue_entries": [{"speaker": "A", "text": "hello"}]},
            {"reference_diarization": [{"speaker": "B", "text": "world"}]},
            [{"speaker": "A", "text": "hello"}],
            [{"speaker": "B", "text": "world"}],
        ),
        ({}, {}, [], []),
    ],
)
def test_extract_segments(result_attr, example_attr, expected_dialogue, expected_reference):
    class Result:
        def __init__(self, attrs):
            for key, value in attrs.items():
                setattr(self, key, value)

    class Example:
        def __init__(self, attrs):
            for key, value in attrs.items():
                setattr(self, key, value)

    result = Result(result_attr)
    example = Example(example_attr)
    dialogue, reference = _extract_segments(result, example)

    assert dialogue == expected_dialogue
    assert reference == expected_reference


def test_validate_and_convert_diarization_success():
    ref_diar = [{"speaker": "Speaker_1", "text": "hello world", "start": 0.0, "end": 1.0}]
    hyp_diar = [{"speaker": "Speaker_A", "text": "hello world", "start": 0.0, "end": 1.0}]

    ref_result, hyp_result = _validate_and_convert_diarization(ref_diar, hyp_diar)

    assert len(ref_result) == len(ref_diar)
    assert len(hyp_result) == len(hyp_diar)


@pytest.mark.parametrize(
    ("ref_diar", "hyp_diar"),
    [
        ([], [{"speaker": "A", "text": "hello"}]),
        ([{"speaker": "A", "text": "hello"}], []),
    ],
)
def test_validate_and_convert_diarization_raises_on_missing_data(ref_diar, hyp_diar):
    with pytest.raises(ValueError, match="Diarization data is required but missing"):
        _validate_and_convert_diarization(ref_diar, hyp_diar)


@pytest.mark.parametrize(
    ("ref_text", "hyp_text", "ref_diar", "hyp_diar", "expected"),
    [
        (
            "hello world good morning",
            "hello world good morning",
            [
                {"speaker": "Speaker_1", "text": "hello world", "start": 0.0, "end": 1.0},
                {"speaker": "Speaker_2", "text": "good morning", "start": 1.0, "end": 2.0},
            ],
            [
                {"speaker": "Speaker_A", "text": "hello world", "start": 0.0, "end": 1.0},
                {"speaker": "Speaker_B", "text": "good morning", "start": 1.0, "end": 2.0},
            ],
            {
                "wer": 0.0,
                "wder": 0.0,
                "speaker_errors": 0,
                "total_words": 4,
                "speaker_count_accuracy": 1.0,
                "ref_speaker_count": 2,
                "hyp_speaker_count": 2,
            },
        ),
        (
            "hello world good morning goodbye",
            "hello world good morning goodbye",
            [
                {"speaker": "Speaker_1", "text": "hello world", "start": 0.0, "end": 1.0},
                {"speaker": "Speaker_2", "text": "good morning", "start": 1.0, "end": 2.0},
                {"speaker": "Speaker_1", "text": "goodbye", "start": 2.0, "end": 2.5},
            ],
            [
                {"speaker": "Speaker_A", "text": "hello world", "start": 0.0, "end": 1.0},
                {"speaker": "Speaker_B", "text": "good morning", "start": 1.0, "end": 2.0},
                {"speaker": "Speaker_B", "text": "goodbye", "start": 2.0, "end": 2.5},
            ],
            {
                "wer": 0.0,
                "wder": 0.2,
                "speaker_errors": 1,
                "total_words": 5,
                "speaker_count_accuracy": 1.0,
                "ref_speaker_count": 2,
                "hyp_speaker_count": 2,
            },
        ),
        (
            "hello world",
            "hello world",
            [
                {"speaker": "Speaker_1", "text": "hello", "start": 0.0, "end": 0.5},
                {"speaker": "Speaker_2", "text": "world", "start": 0.5, "end": 1.0},
            ],
            [
                {"speaker": "Speaker_A", "text": "hello world", "start": 0.0, "end": 1.0},
            ],
            {
                "wer": 0.0,
                "speaker_count_accuracy": 0.0,
                "ref_speaker_count": 2,
                "hyp_speaker_count": 1,
            },
        ),
    ],
)
def test_compute_all_metrics(ref_text, hyp_text, ref_diar, hyp_diar, expected):
    metrics = _compute_all_metrics(ref_text, hyp_text, ref_diar, hyp_diar, processing_speed_ratio=0.5)

    for key, value in expected.items():
        assert getattr(metrics, key) == value

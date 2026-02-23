from __future__ import annotations

import pytest

from evals.transcription.src.core.results import create_summary, save_results
from evals.transcription.src.models import (
    EngineOutput,
    SampleMetrics,
    SampleRow,
    Summary,
    TimingAccumulator,
)


def test_create_summary_basic():
    rows = [
        SampleRow(
            run_id="test_run",
            timestamp="20260223_100000",
            example_id="0",
            engine_version="TestEngine",
            reference_transcript="hello world",
            reference_dialogue_entries=None,
            hypothesis_transcript="hello world",
            hypothesis_dialogue_entries=None,
            metrics=SampleMetrics(
                wer=0.1,
                hits=9,
                substitutions=1,
                deletions=0,
                insertions=0,
                wder=0.0,
                speaker_errors=0,
                total_words=10,
                speaker_count_deviation=0.0,
                ref_speaker_count=2,
                hyp_speaker_count=2,
            ),
            latency_ms={"transcribe": 1000.0},
            latency_recording_ratio=0.5,
            error=None,
        ),
    ]
    timing = TimingAccumulator()
    timing.process_sec = 1.0
    timing.audio_sec = 2.0

    summary = create_summary(
        "TestEngine",
        rows,
        timing,
        "test_run",
        "20260223_100000",
        "ami-v1",
    )

    assert summary.run_id == "test_run"
    assert summary.timestamp == "20260223_100000"
    assert summary.dataset_version == "ami-v1"
    assert summary.engine_version == "TestEngine"
    assert summary.split is None
    assert summary.n_examples == 1
    assert summary.overall_score == pytest.approx(0.9)
    assert "wer" in summary.metrics
    assert summary.metrics["wer"].mean == pytest.approx(0.1)
    assert "transcribe_mean" in summary.latency_ms
    assert summary.latency_ms["transcribe_mean"] == pytest.approx(1000.0)


def test_create_summary_multiple_samples():
    rows = [
        SampleRow(
            run_id="test_run",
            timestamp="20260223_100000",
            example_id="0",
            engine_version="TestEngine",
            reference_transcript="hello world",
            reference_dialogue_entries=None,
            hypothesis_transcript="hello world",
            hypothesis_dialogue_entries=None,
            metrics=SampleMetrics(
                wer=0.1,
                hits=9,
                substitutions=1,
                deletions=0,
                insertions=0,
                wder=0.0,
                speaker_errors=0,
                total_words=10,
                speaker_count_deviation=0.0,
                ref_speaker_count=2,
                hyp_speaker_count=2,
            ),
            latency_ms={"transcribe": 1000.0},
            latency_recording_ratio=0.5,
            error=None,
        ),
        SampleRow(
            run_id="test_run",
            timestamp="20260223_100000",
            example_id="1",
            engine_version="TestEngine",
            reference_transcript="good morning",
            reference_dialogue_entries=None,
            hypothesis_transcript="good morning",
            hypothesis_dialogue_entries=None,
            metrics=SampleMetrics(
                wer=0.2,
                hits=8,
                substitutions=2,
                deletions=0,
                insertions=0,
                wder=0.1,
                speaker_errors=1,
                total_words=10,
                speaker_count_deviation=0.5,
                ref_speaker_count=2,
                hyp_speaker_count=1,
            ),
            latency_ms={"transcribe": 1200.0},
            latency_recording_ratio=0.6,
            error=None,
        ),
    ]
    timing = TimingAccumulator()
    timing.process_sec = 2.0
    timing.audio_sec = 4.0

    summary = create_summary(
        "TestEngine",
        rows,
        timing,
        "test_run",
        "20260223_100000",
        "ami-v1",
    )

    assert summary.run_id == "test_run"
    assert summary.engine_version == "TestEngine"
    assert summary.n_examples == 2
    assert summary.overall_score == pytest.approx(0.85)
    assert "wer" in summary.metrics


def test_create_summary_no_speaker_count_deviation():
    rows = [
        SampleRow(
            run_id="test_run",
            timestamp="20260223_100000",
            example_id="0",
            engine_version="TestEngine",
            reference_transcript="hello world",
            reference_dialogue_entries=None,
            hypothesis_transcript="hello world",
            hypothesis_dialogue_entries=None,
            metrics=SampleMetrics(
                wer=0.1,
                hits=9,
                substitutions=1,
                deletions=0,
                insertions=0,
            ),
            latency_ms={"transcribe": 1000.0},
            latency_recording_ratio=0.5,
            error=None,
        ),
    ]
    timing = TimingAccumulator()
    timing.process_sec = 1.0
    timing.audio_sec = 2.0

    summary = create_summary(
        "TestEngine",
        rows,
        timing,
        "test_run",
        "20260223_100000",
        "ami-v1",
    )

    expected_fields = {
        "run_id": "test_run",
        "timestamp": "20260223_100000",
        "dataset_version": "ami-v1",
        "engine_version": "TestEngine",
        "n_examples": 1,
    }
    for key, value in expected_fields.items():
        assert getattr(summary, key) == value
    assert summary.split is None


def test_save_results_creates_file(tmp_path):
    output_path = tmp_path / "results" / "output.json"

    sample = SampleRow(
        run_id="test_run",
        timestamp="20260223_100000",
        example_id="0",
        engine_version="TestEngine",
        reference_transcript="hello",
        reference_dialogue_entries=None,
        hypothesis_transcript="hello",
        hypothesis_dialogue_entries=None,
        metrics=SampleMetrics(wer=0.1, hits=9, substitutions=1, deletions=0, insertions=0),
        latency_ms={"transcribe": 1000.0},
        latency_recording_ratio=0.5,
        error=None,
    )

    summary = Summary(
        run_id="test_run",
        timestamp="20260223_100000",
        dataset_version="ami-v1",
        engine_version="TestEngine",
        split=None,
        n_examples=1,
        overall_score=0.9,
        metrics={},
        latency_ms={"transcribe_mean": 1000.0},
    )

    results = [EngineOutput(summary=summary, samples=[sample])]
    run_info = {"timestamp": 123456, "num_samples": 1}

    save_results(results, output_path, run_info)

    assert output_path.exists()

    import json

    with output_path.open() as f:
        data = json.load(f)

    expected_run_info = {"timestamp": 123456, "num_samples": 1}
    assert data["run_info"] == expected_run_info

    expected_structure = {
        "summaries_count": 1,
        "engines_count": 1,
        "has_TestEngine": True,
        "TestEngine_samples_count": 1,
    }
    assert len(data["summaries"]) == expected_structure["summaries_count"]
    assert data["summaries"][0]["engine_version"] == "TestEngine"
    assert len(data["engines"]) == expected_structure["engines_count"]
    assert "TestEngine" in data["engines"]
    assert len(data["engines"]["TestEngine"]) == expected_structure["TestEngine_samples_count"]


def test_save_results_multiple_engines(tmp_path):
    output_path = tmp_path / "output.json"

    sample1 = SampleRow(
        run_id="test_run",
        timestamp="20260223_100000",
        example_id="0",
        engine_version="Engine1",
        reference_transcript="hello",
        reference_dialogue_entries=None,
        hypothesis_transcript="hello",
        hypothesis_dialogue_entries=None,
        metrics=SampleMetrics(wer=0.1, hits=9, substitutions=1, deletions=0, insertions=0),
        latency_ms={"transcribe": 1000.0},
        latency_recording_ratio=0.5,
        error=None,
    )

    sample2 = SampleRow(
        run_id="test_run",
        timestamp="20260223_100000",
        example_id="0",
        engine_version="Engine2",
        reference_transcript="world",
        reference_dialogue_entries=None,
        hypothesis_transcript="world",
        hypothesis_dialogue_entries=None,
        metrics=SampleMetrics(wer=0.2, hits=8, substitutions=2, deletions=0, insertions=0),
        latency_ms={"transcribe": 1500.0},
        latency_recording_ratio=0.6,
        error=None,
    )

    summary1 = Summary(
        run_id="test_run",
        timestamp="20260223_100000",
        dataset_version="ami-v1",
        engine_version="Engine1",
        split=None,
        n_examples=1,
        overall_score=0.9,
        metrics={},
        latency_ms={"transcribe_mean": 1000.0},
    )

    summary2 = Summary(
        run_id="test_run",
        timestamp="20260223_100000",
        dataset_version="ami-v1",
        engine_version="Engine2",
        split=None,
        n_examples=1,
        overall_score=0.8,
        metrics={},
        latency_ms={"transcribe_mean": 1500.0},
    )

    results = [
        EngineOutput(summary=summary1, samples=[sample1]),
        EngineOutput(summary=summary2, samples=[sample2]),
    ]
    run_info = {"timestamp": 123456}

    save_results(results, output_path, run_info)

    import json

    with output_path.open() as f:
        data = json.load(f)

    expected_structure = {
        "summaries_count": 2,
        "engines_count": 2,
        "engines": ["Engine1", "Engine2"],
    }
    assert len(data["summaries"]) == expected_structure["summaries_count"]
    assert len(data["engines"]) == expected_structure["engines_count"]
    for engine in expected_structure["engines"]:
        assert engine in data["engines"]

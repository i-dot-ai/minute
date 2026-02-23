from __future__ import annotations

from evals.transcription.src.core.runner import (
    _compute_diarization_metrics,
    _extract_segments,
    _process_diarization,
)
from evals.transcription.src.models import SampleMetrics


def test_extract_segments_with_attributes():
    class Result:
        def __init__(self):
            self.dialogue_entries = [{"speaker": "A", "text": "hello"}]

    class Example:
        def __init__(self):
            self.reference_diarization = [{"speaker": "B", "text": "world"}]

    result = Result()
    example = Example()
    dialogue, reference = _extract_segments(result, example)

    assert dialogue == [{"speaker": "A", "text": "hello"}]
    assert reference == [{"speaker": "B", "text": "world"}]


def test_extract_segments_without_attributes():
    result = {}
    example = {}
    dialogue, reference = _extract_segments(result, example)

    assert dialogue == []
    assert reference == []


def test_process_diarization_with_data():
    reference_diarization = [{"speaker": "Speaker_1", "text": "hello world", "start": 0.0, "end": 1.0}]
    dialogue_entries = [{"speaker": "Speaker_A", "text": "hello world", "start": 0.0, "end": 1.0}]
    metrics = SampleMetrics(wer=0.0, hits=2, substitutions=0, deletions=0, insertions=0)

    ref_diar, hyp_diar = _process_diarization(reference_diarization, dialogue_entries, metrics)

    assert len(ref_diar) == 1
    assert len(hyp_diar) == 1

    expected_ref = {"speaker": "Speaker_1", "text": "hello world", "start": 0.0, "end": 1.0}
    expected_hyp = {"speaker": "Speaker_A", "text": "hello world", "start": 0.0, "end": 1.0}
    assert ref_diar[0] == expected_ref
    assert hyp_diar[0] == expected_hyp
    assert metrics.wder == 0.0
    assert metrics.speaker_errors == 0
    assert metrics.total_words == 2


def test_process_diarization_empty_reference():
    metrics = SampleMetrics(wer=0.0, hits=0, substitutions=0, deletions=0, insertions=0)

    ref_diar, hyp_diar = _process_diarization([], [{"speaker": "A", "text": "hello"}], metrics)

    assert ref_diar == []
    assert hyp_diar == []
    assert metrics.wder is None


def test_process_diarization_empty_dialogue():
    metrics = SampleMetrics(wer=0.0, hits=0, substitutions=0, deletions=0, insertions=0)

    ref_diar, hyp_diar = _process_diarization([{"speaker": "A", "text": "hello"}], [], metrics)

    assert ref_diar == []
    assert hyp_diar == []


def test_compute_diarization_metrics_updates_metrics():
    ref_diar = [
        {"speaker": "Speaker_1", "text": "hello world", "start": 0.0, "end": 1.0},
        {"speaker": "Speaker_2", "text": "good morning", "start": 1.0, "end": 2.0},
    ]
    hyp_diar = [
        {"speaker": "Speaker_A", "text": "hello world", "start": 0.0, "end": 1.0},
        {"speaker": "Speaker_B", "text": "good morning", "start": 1.0, "end": 2.0},
    ]
    metrics = SampleMetrics(wer=0.0, hits=4, substitutions=0, deletions=0, insertions=0)

    _compute_diarization_metrics(ref_diar, hyp_diar, metrics)

    expected_metrics = {
        "wder": 0.0,
        "speaker_errors": 0,
        "total_words": 4,
        "speaker_count_deviation": 0.0,
        "ref_speaker_count": 2,
        "hyp_speaker_count": 2,
    }
    for key, value in expected_metrics.items():
        assert getattr(metrics, key) == value


def test_compute_diarization_metrics_with_speaker_errors():
    ref_diar = [
        {"speaker": "Speaker_1", "text": "hello world", "start": 0.0, "end": 1.0},
        {"speaker": "Speaker_2", "text": "good morning", "start": 1.0, "end": 2.0},
        {"speaker": "Speaker_1", "text": "goodbye", "start": 2.0, "end": 2.5},
    ]
    hyp_diar = [
        {"speaker": "Speaker_A", "text": "hello world", "start": 0.0, "end": 1.0},
        {"speaker": "Speaker_B", "text": "good morning", "start": 1.0, "end": 2.0},
        {"speaker": "Speaker_B", "text": "goodbye", "start": 2.0, "end": 2.5},
    ]
    metrics = SampleMetrics(wer=0.0, hits=5, substitutions=0, deletions=0, insertions=0)

    _compute_diarization_metrics(ref_diar, hyp_diar, metrics)

    assert metrics.wder == 0.2
    assert metrics.speaker_errors == 1
    assert metrics.total_words == 5
    assert metrics.speaker_count_deviation == 0.0
    assert metrics.ref_speaker_count == 2
    assert metrics.hyp_speaker_count == 2


def test_compute_diarization_metrics_with_speaker_count_mismatch():
    ref_diar = [
        {"speaker": "Speaker_1", "text": "hello", "start": 0.0, "end": 0.5},
        {"speaker": "Speaker_2", "text": "world", "start": 0.5, "end": 1.0},
    ]
    hyp_diar = [
        {"speaker": "Speaker_A", "text": "hello world", "start": 0.0, "end": 1.0},
    ]
    metrics = SampleMetrics(wer=0.0, hits=2, substitutions=0, deletions=0, insertions=0)

    _compute_diarization_metrics(ref_diar, hyp_diar, metrics)

    assert metrics.speaker_count_deviation == 1.0
    assert metrics.ref_speaker_count == 2
    assert metrics.hyp_speaker_count == 1

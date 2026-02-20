from __future__ import annotations

from evals.transcription.src.core.metrics.diarization import compute_wder
from evals.transcription.src.core.metrics.jaccard import compute_jaccard_wer
from evals.transcription.src.core.metrics.speaker_count import compute_speaker_count_metrics


def test_compute_wder_perfect_match():
    ref_segments = [
        {"speaker": "Speaker_1", "text": "hello world", "start": 0.0, "end": 1.0},
        {"speaker": "Speaker_2", "text": "good morning", "start": 1.0, "end": 2.0},
    ]
    hyp_segments = [
        {"speaker": "Speaker_A", "text": "hello world", "start": 0.0, "end": 1.0},
        {"speaker": "Speaker_B", "text": "good morning", "start": 1.0, "end": 2.0},
    ]

    result = compute_wder(ref_segments, hyp_segments)
    assert result["wder"] == 0.0
    assert result["speaker_errors"] == 0
    assert result["total_words"] == 4


def test_compute_wder_speaker_mismatch():
    ref_segments = [
        {"speaker": "Speaker_1", "text": "hello world", "start": 0.0, "end": 1.0},
        {"speaker": "Speaker_1", "text": "goodbye", "start": 1.0, "end": 1.5},
    ]
    hyp_segments = [
        {"speaker": "Speaker_2", "text": "hello world", "start": 0.0, "end": 1.0},
        {"speaker": "Speaker_1", "text": "goodbye", "start": 1.0, "end": 1.5},
    ]

    result = compute_wder(ref_segments, hyp_segments)
    assert result["wder"] > 0.0
    assert result["speaker_errors"] > 0
    assert result["total_words"] == 3


def test_compute_wder_empty_segments():
    result = compute_wder([], [])
    assert result["wder"] == 0.0
    assert result["speaker_errors"] == 0
    assert result["total_words"] == 0


def test_compute_wder_missing_hypothesis():
    ref_segments = [
        {"speaker": "Speaker_1", "text": "hello world", "start": 0.0, "end": 1.0},
    ]
    result = compute_wder(ref_segments, [])
    assert result["wder"] == 0.0
    assert result["speaker_errors"] == 0
    assert result["total_words"] == 2


def test_compute_jaccard_wer_perfect_match():
    result = compute_jaccard_wer(["hello world"], ["hello world"])
    assert result["jaccard_wer"] == 0.0


def test_compute_jaccard_wer_partial_overlap():
    result = compute_jaccard_wer(["hello world test"], ["hello world example"])
    assert 0.0 < result["jaccard_wer"] < 1.0


def test_compute_jaccard_wer_no_overlap():
    result = compute_jaccard_wer(["hello world"], ["goodbye universe"])
    assert result["jaccard_wer"] == 1.0


def test_compute_speaker_count_metrics_perfect_match():
    ref_segments = [
        {"speaker": "Speaker_1", "text": "hello", "start": 0.0, "end": 0.5},
        {"speaker": "Speaker_2", "text": "world", "start": 0.5, "end": 1.0},
    ]
    hyp_segments = [
        {"speaker": "Speaker_A", "text": "hello", "start": 0.0, "end": 0.5},
        {"speaker": "Speaker_B", "text": "world", "start": 0.5, "end": 1.0},
    ]

    result = compute_speaker_count_metrics(ref_segments, hyp_segments)
    assert result["speaker_count_accuracy"] == 1.0
    assert result["ref_speaker_count"] == 2
    assert result["hyp_speaker_count"] == 2


def test_compute_speaker_count_metrics_mismatch():
    ref_segments = [
        {"speaker": "Speaker_1", "text": "hello", "start": 0.0, "end": 0.5},
        {"speaker": "Speaker_2", "text": "world", "start": 0.5, "end": 1.0},
    ]
    hyp_segments = [
        {"speaker": "Speaker_A", "text": "hello world", "start": 0.0, "end": 1.0},
    ]

    result = compute_speaker_count_metrics(ref_segments, hyp_segments)
    assert result["speaker_count_accuracy"] == 0.0
    assert result["ref_speaker_count"] == 2
    assert result["hyp_speaker_count"] == 1


def test_compute_speaker_count_metrics_empty():
    result = compute_speaker_count_metrics([], [])
    assert result["speaker_count_accuracy"] == 1.0
    assert result["ref_speaker_count"] == 0
    assert result["hyp_speaker_count"] == 0


def test_compute_wder_more_ref_speakers_than_hyp():
    ref_segments = [
        {"speaker": "Speaker_1", "text": "hello world", "start": 0.0, "end": 1.0},
        {"speaker": "Speaker_2", "text": "good morning", "start": 1.0, "end": 2.0},
        {"speaker": "Speaker_3", "text": "goodbye", "start": 2.0, "end": 2.5},
    ]
    hyp_segments = [
        {"speaker": "Speaker_A", "text": "hello world", "start": 0.0, "end": 1.0},
        {"speaker": "Speaker_B", "text": "good morning goodbye", "start": 1.0, "end": 2.5},
    ]

    result = compute_wder(ref_segments, hyp_segments)
    assert result["total_words"] == 5
    assert result["speaker_errors"] == 1


def test_compute_wder_hyp_speaker_no_overlap():
    ref_segments = [
        {"speaker": "Speaker_1", "text": "hello world", "start": 0.0, "end": 1.0},
    ]
    hyp_segments = [
        {"speaker": "Speaker_A", "text": "hello world", "start": 0.0, "end": 1.0},
        {"speaker": "Speaker_B", "text": "extra words", "start": 1.0, "end": 1.5},
    ]

    result = compute_wder(ref_segments, hyp_segments)
    assert result["total_words"] == 2
    assert result["speaker_errors"] == 0


def test_compute_wder_all_words_wrong_speaker():
    ref_segments = [
        {"speaker": "Speaker_1", "text": "hello world", "start": 0.0, "end": 1.0},
        {"speaker": "Speaker_2", "text": "good morning", "start": 1.0, "end": 2.0},
    ]
    hyp_segments = [
        {"speaker": "Speaker_2", "text": "hello world", "start": 0.0, "end": 1.0},
        {"speaker": "Speaker_1", "text": "good morning", "start": 1.0, "end": 2.0},
    ]

    result = compute_wder(ref_segments, hyp_segments)
    assert result["wder"] == 0.0
    assert result["speaker_errors"] == 0
    assert result["total_words"] == 4


def test_compute_wder_partial_speaker_errors():
    ref_segments = [
        {"speaker": "Speaker_1", "text": "hello world", "start": 0.0, "end": 1.0},
        {"speaker": "Speaker_2", "text": "good morning", "start": 1.0, "end": 2.0},
        {"speaker": "Speaker_1", "text": "goodbye", "start": 2.0, "end": 2.5},
    ]
    hyp_segments = [
        {"speaker": "Speaker_A", "text": "hello world", "start": 0.0, "end": 1.0},
        {"speaker": "Speaker_B", "text": "good morning", "start": 1.0, "end": 2.0},
        {"speaker": "Speaker_B", "text": "goodbye", "start": 2.0, "end": 2.5},
    ]

    result = compute_wder(ref_segments, hyp_segments)
    assert result["total_words"] == 5
    assert result["speaker_errors"] == 1
    assert result["wder"] == 0.2


def test_compute_wder_with_punctuation_and_case():
    ref_segments = [
        {"speaker": "Speaker_1", "text": "Hello, World!", "start": 0.0, "end": 1.0},
    ]
    hyp_segments = [
        {"speaker": "Speaker_A", "text": "hello world", "start": 0.0, "end": 1.0},
    ]

    result = compute_wder(ref_segments, hyp_segments)
    assert result["wder"] == 0.0
    assert result["speaker_errors"] == 0
    assert result["total_words"] == 2


def test_compute_wder_three_speakers_optimal_mapping():
    ref_segments = [
        {"speaker": "Speaker_1", "text": "one two three", "start": 0.0, "end": 1.0},
        {"speaker": "Speaker_2", "text": "four five six", "start": 1.0, "end": 2.0},
        {"speaker": "Speaker_3", "text": "seven eight nine", "start": 2.0, "end": 3.0},
    ]
    hyp_segments = [
        {"speaker": "Speaker_C", "text": "one two three", "start": 0.0, "end": 1.0},
        {"speaker": "Speaker_A", "text": "four five six", "start": 1.0, "end": 2.0},
        {"speaker": "Speaker_B", "text": "seven eight nine", "start": 2.0, "end": 3.0},
    ]

    result = compute_wder(ref_segments, hyp_segments)
    assert result["wder"] == 0.0
    assert result["speaker_errors"] == 0
    assert result["total_words"] == 9


def test_compute_wder_with_transcription_errors():
    ref_segments = [
        {"speaker": "Speaker_1", "text": "hello world test", "start": 0.0, "end": 1.0},
    ]
    hyp_segments = [
        {"speaker": "Speaker_A", "text": "hello world", "start": 0.0, "end": 1.0},
    ]

    result = compute_wder(ref_segments, hyp_segments)
    assert result["total_words"] == 3
    assert result["speaker_errors"] == 0


def test_compute_jaccard_wer_empty_inputs():
    result = compute_jaccard_wer([], [])
    assert result["jaccard_wer"] == 0.0


def test_compute_jaccard_wer_empty_reference():
    result = compute_jaccard_wer([], ["hello world"])
    assert result["jaccard_wer"] == 0.0


def test_compute_jaccard_wer_empty_hypothesis():
    result = compute_jaccard_wer(["hello world"], [])
    assert result["jaccard_wer"] == 0.0


def test_compute_jaccard_wer_case_insensitive():
    result = compute_jaccard_wer(["Hello World"], ["hello world"])
    assert result["jaccard_wer"] == 0.0


def test_compute_jaccard_wer_punctuation_handling():
    result = compute_jaccard_wer(["Hello, world!"], ["Hello world"])
    assert result["jaccard_wer"] == 0.0


def test_compute_jaccard_wer_duplicate_words():
    result = compute_jaccard_wer(["hello hello world"], ["hello world world"])
    assert result["jaccard_wer"] == 0.0


def test_compute_jaccard_wer_subset():
    result = compute_jaccard_wer(["hello world test"], ["hello world"])
    assert result["jaccard_wer"] > 0.0
    assert result["jaccard_wer"] < 1.0


def test_compute_speaker_count_metrics_more_hyp_speakers():
    ref_segments = [
        {"speaker": "Speaker_1", "text": "hello", "start": 0.0, "end": 0.5},
    ]
    hyp_segments = [
        {"speaker": "Speaker_A", "text": "hello", "start": 0.0, "end": 0.5},
        {"speaker": "Speaker_B", "text": "world", "start": 0.5, "end": 1.0},
    ]

    result = compute_speaker_count_metrics(ref_segments, hyp_segments)
    assert result["speaker_count_accuracy"] == 0.0
    assert result["ref_speaker_count"] == 1
    assert result["hyp_speaker_count"] == 2
    assert result["absolute_error"] == 1


def test_compute_speaker_count_metrics_large_difference():
    ref_segments = [
        {"speaker": "Speaker_1", "text": "hello", "start": 0.0, "end": 0.5},
        {"speaker": "Speaker_2", "text": "world", "start": 0.5, "end": 1.0},
        {"speaker": "Speaker_3", "text": "test", "start": 1.0, "end": 1.5},
    ]
    hyp_segments = [
        {"speaker": "Speaker_A", "text": "hello world test", "start": 0.0, "end": 1.5},
    ]

    result = compute_speaker_count_metrics(ref_segments, hyp_segments)
    assert result["speaker_count_accuracy"] == 0.0
    assert result["ref_speaker_count"] == 3
    assert result["hyp_speaker_count"] == 1
    assert result["absolute_error"] == 2


def test_compute_speaker_count_metrics_duplicate_speaker_names():
    ref_segments = [
        {"speaker": "Speaker_1", "text": "hello", "start": 0.0, "end": 0.5},
        {"speaker": "Speaker_1", "text": "world", "start": 0.5, "end": 1.0},
        {"speaker": "Speaker_2", "text": "test", "start": 1.0, "end": 1.5},
    ]
    hyp_segments = [
        {"speaker": "Speaker_A", "text": "hello", "start": 0.0, "end": 0.5},
        {"speaker": "Speaker_A", "text": "world", "start": 0.5, "end": 1.0},
        {"speaker": "Speaker_B", "text": "test", "start": 1.0, "end": 1.5},
    ]

    result = compute_speaker_count_metrics(ref_segments, hyp_segments)
    assert result["speaker_count_accuracy"] == 1.0
    assert result["ref_speaker_count"] == 2
    assert result["hyp_speaker_count"] == 2
    assert result["absolute_error"] == 0

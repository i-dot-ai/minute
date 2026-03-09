from __future__ import annotations

import pytest

from evals.transcription.src.core.metrics import compute_speaker_count_metrics, compute_wder


@pytest.mark.parametrize(
    ("ref_segments", "hyp_segments", "expected"),
    [
        (
            [
                {"speaker": "Speaker_1", "text": "hello world", "start": 0.0, "end": 1.0},
                {"speaker": "Speaker_2", "text": "good morning", "start": 1.0, "end": 2.0},
            ],
            [
                {"speaker": "Speaker_A", "text": "hello world", "start": 0.0, "end": 1.0},
                {"speaker": "Speaker_B", "text": "good morning", "start": 1.0, "end": 2.0},
            ],
            {"wder": 0.0, "speaker_errors": 0, "total_words": 4},
        ),
        ([], [], {"wder": 0.0, "speaker_errors": 0, "total_words": 0}),
        (
            [{"speaker": "Speaker_1", "text": "hello world", "start": 0.0, "end": 1.0}],
            [],
            {"wder": 0.0, "speaker_errors": 0, "total_words": 2},
        ),
        (
            [
                {"speaker": "Speaker_1", "text": "hello world", "start": 0.0, "end": 1.0},
                {"speaker": "Speaker_2", "text": "good morning", "start": 1.0, "end": 2.0},
                {"speaker": "Speaker_3", "text": "goodbye", "start": 2.0, "end": 2.5},
            ],
            [
                {"speaker": "Speaker_A", "text": "hello world", "start": 0.0, "end": 1.0},
                {"speaker": "Speaker_B", "text": "good morning goodbye", "start": 1.0, "end": 2.5},
            ],
            {"wder": 0.2, "speaker_errors": 1, "total_words": 5},
        ),
        (
            [{"speaker": "Speaker_1", "text": "hello world", "start": 0.0, "end": 1.0}],
            [
                {"speaker": "Speaker_A", "text": "hello world", "start": 0.0, "end": 1.0},
                {"speaker": "Speaker_B", "text": "extra words", "start": 1.0, "end": 1.5},
            ],
            {"wder": 0.0, "speaker_errors": 0, "total_words": 2},
        ),
        (
            [
                {"speaker": "Speaker_1", "text": "hello world", "start": 0.0, "end": 1.0},
                {"speaker": "Speaker_2", "text": "good morning", "start": 1.0, "end": 2.0},
            ],
            [
                {"speaker": "Speaker_2", "text": "hello world", "start": 0.0, "end": 1.0},
                {"speaker": "Speaker_1", "text": "good morning", "start": 1.0, "end": 2.0},
            ],
            {"wder": 0.0, "speaker_errors": 0, "total_words": 4},
        ),
        (
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
            {"wder": 0.2, "speaker_errors": 1, "total_words": 5},
        ),
        (
            [{"speaker": "Speaker_1", "text": "Hello, World!", "start": 0.0, "end": 1.0}],
            [{"speaker": "Speaker_A", "text": "hello world", "start": 0.0, "end": 1.0}],
            {"wder": 0.0, "speaker_errors": 0, "total_words": 2},
        ),
        (
            [
                {"speaker": "Speaker_1", "text": "one two three", "start": 0.0, "end": 1.0},
                {"speaker": "Speaker_2", "text": "four five six", "start": 1.0, "end": 2.0},
                {"speaker": "Speaker_3", "text": "seven eight nine", "start": 2.0, "end": 3.0},
            ],
            [
                {"speaker": "Speaker_C", "text": "one two three", "start": 0.0, "end": 1.0},
                {"speaker": "Speaker_A", "text": "four five six", "start": 1.0, "end": 2.0},
                {"speaker": "Speaker_B", "text": "seven eight nine", "start": 2.0, "end": 3.0},
            ],
            {"wder": 0.0, "speaker_errors": 0, "total_words": 9},
        ),
        (
            [{"speaker": "Speaker_1", "text": "hello world test", "start": 0.0, "end": 1.0}],
            [{"speaker": "Speaker_A", "text": "hello world", "start": 0.0, "end": 1.0}],
            {"wder": 0.0, "speaker_errors": 0, "total_words": 3},
        ),
    ],
)
def test_compute_wder(ref_segments, hyp_segments, expected):
    result = compute_wder(ref_segments, hyp_segments)
    assert result == expected


@pytest.mark.parametrize(
    ("ref_segments", "hyp_segments", "expected"),
    [
        (
            [
                {"speaker": "Speaker_1", "text": "hello", "start": 0.0, "end": 0.5},
                {"speaker": "Speaker_2", "text": "world", "start": 0.5, "end": 1.0},
            ],
            [
                {"speaker": "Speaker_A", "text": "hello", "start": 0.0, "end": 0.5},
                {"speaker": "Speaker_B", "text": "world", "start": 0.5, "end": 1.0},
            ],
            {"speaker_count_accuracy": 1.0, "ref_speaker_count": 2, "hyp_speaker_count": 2, "absolute_error": 0},
        ),
        (
            [
                {"speaker": "Speaker_1", "text": "hello", "start": 0.0, "end": 0.5},
                {"speaker": "Speaker_2", "text": "world", "start": 0.5, "end": 1.0},
            ],
            [{"speaker": "Speaker_A", "text": "hello world", "start": 0.0, "end": 1.0}],
            {"speaker_count_accuracy": 0.0, "ref_speaker_count": 2, "hyp_speaker_count": 1, "absolute_error": 1},
        ),
        (
            [],
            [],
            {"speaker_count_accuracy": 1.0, "ref_speaker_count": 0, "hyp_speaker_count": 0, "absolute_error": 0},
        ),
        (
            [{"speaker": "Speaker_1", "text": "hello", "start": 0.0, "end": 0.5}],
            [
                {"speaker": "Speaker_A", "text": "hello", "start": 0.0, "end": 0.5},
                {"speaker": "Speaker_B", "text": "world", "start": 0.5, "end": 1.0},
            ],
            {"speaker_count_accuracy": 0.0, "ref_speaker_count": 1, "hyp_speaker_count": 2, "absolute_error": 1},
        ),
        (
            [
                {"speaker": "Speaker_1", "text": "hello", "start": 0.0, "end": 0.5},
                {"speaker": "Speaker_2", "text": "world", "start": 0.5, "end": 1.0},
                {"speaker": "Speaker_3", "text": "test", "start": 1.0, "end": 1.5},
            ],
            [{"speaker": "Speaker_A", "text": "hello world test", "start": 0.0, "end": 1.5}],
            {"speaker_count_accuracy": 0.0, "ref_speaker_count": 3, "hyp_speaker_count": 1, "absolute_error": 2},
        ),
        (
            [
                {"speaker": "Speaker_1", "text": "hello", "start": 0.0, "end": 0.5},
                {"speaker": "Speaker_1", "text": "world", "start": 0.5, "end": 1.0},
                {"speaker": "Speaker_2", "text": "test", "start": 1.0, "end": 1.5},
            ],
            [
                {"speaker": "Speaker_A", "text": "hello", "start": 0.0, "end": 0.5},
                {"speaker": "Speaker_A", "text": "world", "start": 0.5, "end": 1.0},
                {"speaker": "Speaker_B", "text": "test", "start": 1.0, "end": 1.5},
            ],
            {"speaker_count_accuracy": 1.0, "ref_speaker_count": 2, "hyp_speaker_count": 2, "absolute_error": 0},
        ),
    ],
)
def test_compute_speaker_count_metrics(ref_segments, hyp_segments, expected):
    result = compute_speaker_count_metrics(ref_segments, hyp_segments)
    assert result == expected

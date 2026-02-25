from __future__ import annotations

import pytest

from evals.transcription.src.core.metrics import compute_wer_metrics, normalise_text


@pytest.mark.parametrize(
    ("input_text", "expected"),
    [
        ("", ""),
        ("  Hello,   WORLD!!  ", "hello world"),
    ],
)
def test_normalise_text_edge_cases(input_text, expected):
    assert normalise_text(input_text) == expected


@pytest.mark.parametrize(
    ("reference", "hypothesis"),
    [
        ([""], ["hello world"]),
        ([""], [""]),
        ([], []),
    ],
)
def test_compute_wer_metrics_empty_reference_raises_error(reference, hypothesis):
    with pytest.raises(ValueError, match=".*"):
        compute_wer_metrics(reference, hypothesis)


@pytest.mark.parametrize(
    ("reference", "hypothesis", "expected_metrics"),
    [
        (
            ["hello world"],
            [""],
            {"wer": 1.0, "hits": 0, "deletions": 2, "insertions": 0},
        ),
        (
            ["hello world"],
            ["hello world"],
            {"wer": 0.0, "hits": 2, "substitutions": 0, "deletions": 0, "insertions": 0},
        ),
        (
            ["hello world"],
            ["goodbye universe"],
            {"wer": 1.0, "hits": 0, "substitutions": 2, "deletions": 0, "insertions": 0},
        ),
        (
            ["hello world"],
            ["hello there world"],
            {"insertions": 1, "deletions": 0, "substitutions": 0},
        ),
    ],
)
def test_compute_wer_metrics(reference, hypothesis, expected_metrics):
    metrics = compute_wer_metrics(reference, hypothesis)
    actual_metrics = {k: getattr(metrics, k) for k in expected_metrics}
    assert expected_metrics == actual_metrics

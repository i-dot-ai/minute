from __future__ import annotations

import pytest

from evals.transcription.src.core.metrics.transcription import compute_wer_metrics
from evals.transcription.src.core.metrics.transforms import normalise_text


def test_normalise_text_edge_cases():
    assert normalise_text("") == ""
    assert normalise_text("  Hello,   WORLD!!  ") == "hello world"


def test_compute_wer_metrics_empty_reference_raises_error():
    with pytest.raises(ValueError, match=".*"):
        compute_wer_metrics([""], ["hello world"])

    with pytest.raises(ValueError, match=".*"):
        compute_wer_metrics([""], [""])

    with pytest.raises(ValueError, match=".*"):
        compute_wer_metrics([], [])


def test_compute_wer_metrics_empty_hypothesis():
    metrics = compute_wer_metrics(["hello world"], [""])
    assert metrics["wer"] == 1.0
    assert metrics["hits"] == 0
    assert metrics["deletions"] == 2
    assert metrics["insertions"] == 0


def test_compute_wer_metrics_perfect_match():
    metrics = compute_wer_metrics(["hello world"], ["hello world"])
    assert metrics["wer"] == 0.0
    assert metrics["hits"] == 2
    assert metrics["substitutions"] == 0
    assert metrics["deletions"] == 0
    assert metrics["insertions"] == 0


def test_compute_wer_metrics_all_substitutions():
    metrics = compute_wer_metrics(["hello world"], ["goodbye universe"])
    assert metrics["wer"] == 1.0
    assert metrics["hits"] == 0
    assert metrics["substitutions"] == 2
    assert metrics["deletions"] == 0
    assert metrics["insertions"] == 0


def test_compute_wer_metrics_small_example():
    metrics = compute_wer_metrics(["hello world"], ["hello there world"])
    assert metrics["insertions"] == 1
    assert metrics["deletions"] == 0
    assert metrics["substitutions"] == 0

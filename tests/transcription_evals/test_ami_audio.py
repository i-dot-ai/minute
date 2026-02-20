from __future__ import annotations

import numpy as np

from evals.transcription.src.core.ami import audio
from evals.transcription.src.core.ami.loader import _apply_cutoff


def test_mix_utterances_aligns_and_concatenates_text():
    utterances = [
        {
            "audio": {"array": np.array([0.5, 0.5], dtype=np.float32), "sampling_rate": 16000},
            "begin_time": 0.0,
            "end_time": 2 / 16000,
            "text": "hello",
        },
        {
            "audio": {"array": np.array([0.25, 0.25], dtype=np.float32), "sampling_rate": 16000},
            "begin_time": 2 / 16000,
            "end_time": 4 / 16000,
            "text": "world",
        },
    ]

    mixed, text = audio.mix_utterances(utterances, target_sample_rate=16000)

    assert text == "hello world"
    assert len(mixed) == 4
    np.testing.assert_allclose(mixed, np.array([0.5, 0.5, 0.25, 0.25], dtype=np.float32))


def test_mix_utterances_overlaps_and_normalises_peak():
    utterances = [
        {
            "audio": {"array": np.array([1.0, 1.0], dtype=np.float32), "sampling_rate": 16000},
            "begin_time": 0.0,
            "end_time": 2 / 16000,
            "text": "one",
        },
        {
            "audio": {"array": np.array([1.0, 1.0], dtype=np.float32), "sampling_rate": 16000},
            "begin_time": 0.0,
            "end_time": 2 / 16000,
            "text": "two",
        },
    ]

    mixed, _text = audio.mix_utterances(utterances, target_sample_rate=16000)

    np.testing.assert_allclose(mixed, np.array([2.0, 2.0], dtype=np.float32))


def test_apply_cutoff_respects_duration():
    utterances = [
        {"begin_time": 0.0, "end_time": 1.0, "text": "a"},
        {"begin_time": 1.0, "end_time": 2.5, "text": "b"},
        {"begin_time": 2.5, "end_time": 4.0, "text": "c"},
    ]

    trimmed = _apply_cutoff(utterances, cutoff_time=2.0)

    assert [u["text"] for u in trimmed] == ["a"]

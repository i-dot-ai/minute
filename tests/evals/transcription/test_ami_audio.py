from __future__ import annotations

import numpy as np

from evals.transcription.src.core.ami import audio
from evals.transcription.src.core.ami.loader import _apply_cutoff
from evals.transcription.src.models import RawAudioDict, RawDatasetRow


def _create_utterance(audio_id: str, text: str, audio_array: np.ndarray, begin: float, end: float) -> RawDatasetRow:
    return RawDatasetRow(
        meeting_id="test",
        audio_id=audio_id,
        text=text,
        audio=RawAudioDict(array=audio_array, sampling_rate=16000),
        begin_time=begin,
        end_time=end,
        microphone_id="mic1",
        speaker_id="spk1",
    )


def test_mix_utterances_aligns_and_concatenates_text():
    utterances = [
        _create_utterance("1", "hello", np.array([0.5, 0.5], dtype=np.float32), 0.0, 2 / 16000),
        _create_utterance("2", "world", np.array([0.25, 0.25], dtype=np.float32), 2 / 16000, 4 / 16000),
    ]

    mixed, text = audio.mix_utterances(utterances, target_sample_rate=16000)

    assert text == "hello world"
    assert len(mixed) == 4
    np.testing.assert_allclose(mixed, np.array([0.5, 0.5, 0.25, 0.25], dtype=np.float32))


def test_mix_utterances_overlaps_and_normalises_peak():
    utterances = [
        _create_utterance("1", "one", np.array([1.0, 1.0], dtype=np.float32), 0.0, 2 / 16000),
        _create_utterance("2", "two", np.array([1.0, 1.0], dtype=np.float32), 0.0, 2 / 16000),
    ]

    mixed, _text = audio.mix_utterances(utterances, target_sample_rate=16000)

    np.testing.assert_allclose(mixed, np.array([2.0, 2.0], dtype=np.float32))


def test_apply_cutoff_respects_duration():
    utterances = [
        _create_utterance("1", "a", np.array([0.0], dtype=np.float32), 0.0, 1.0),
        _create_utterance("2", "b", np.array([0.0], dtype=np.float32), 1.0, 2.5),
        _create_utterance("3", "c", np.array([0.0], dtype=np.float32), 2.5, 4.0),
    ]

    trimmed = _apply_cutoff(utterances, cutoff_time=2.0)

    assert [u.text for u in trimmed] == ["a"]

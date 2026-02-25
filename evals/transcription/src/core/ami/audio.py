import logging
from typing import List

import numpy
from common.constants import TARGET_SAMPLE_RATE

from evals.transcription.src.models import RawDatasetRow

logger = logging.getLogger(__name__)


def mix_utterances(
    utterances: List[RawDatasetRow], target_sample_rate: int = TARGET_SAMPLE_RATE
) -> tuple[numpy.ndarray, str]:
    """
    Mixes multiple utterances into a single audio array and concatenates their texts.
    Returns a tuple of (mixed_audio, text).
    """
    if not utterances:
        return numpy.array([], dtype=numpy.float32), ""

    utterances_sorted = sorted(utterances, key=lambda x: x.begin_time)

    max_end_time = max(utterance.end_time for utterance in utterances_sorted)
    total_samples = int(numpy.ceil(max_end_time * target_sample_rate))

    mixed_audio = numpy.zeros(total_samples, dtype=numpy.float32)
    text_parts = []

    for utterance in utterances_sorted:
        audio_array = utterance.audio.array
        begin_time = utterance.begin_time
        text = utterance.text

        start_sample = int(begin_time * target_sample_rate)
        end_sample = start_sample + len(audio_array)

        if end_sample > len(mixed_audio):
            end_sample = len(mixed_audio)
            audio_array = audio_array[: end_sample - start_sample]

        mixed_audio[start_sample:end_sample] += audio_array

        if text.strip():
            text_parts.append(text)

    full_text = " ".join(text_parts)

    return mixed_audio, full_text


def compute_duration(audio: numpy.ndarray, sample_rate: int = TARGET_SAMPLE_RATE) -> float:
    """
    Computes the duration of the audio in seconds.
    """
    return float(len(audio) / sample_rate)

from typing import TypedDict, cast

import jiwer

from common.database.postgres_models import DialogueEntry
from evals.transcription.src.core.metrics.diarization import (
    find_optimal_speaker_mapping,
    flatten_segments_to_word_speaker_pairs,
)
from evals.transcription.src.core.metrics.transforms import jiwer_transform, normalise_text
from evals.transcription.src.models import DiarizationSegment, SampleRow


class SegmentDict(TypedDict):
    speaker: str
    text: str


class SegmentWithTiming(TypedDict):
    speaker: str
    text: str
    start_time: float
    end_time: float


class WordSpeakerPair(TypedDict):
    word: str
    speaker: str
    start: float
    end: float


def format_segments_with_speakers(
    segments: list[DialogueEntry] | list[SegmentDict],
    reference_segments: list[DialogueEntry] | list[SegmentDict] | None = None,
) -> str:
    """
    Format segments with speaker labels and normalized text.

    If reference_segments provided, applies optimal speaker mapping to align
    hypothesis speakers with reference speakers before formatting.
    """
    if not segments:
        return ""

    speaker_mapping: dict[str, str] = {}

    if reference_segments:
        ref_diar = _segments_to_diarization_format(reference_segments)
        hyp_diar = _segments_to_diarization_format(segments)

        ref_pairs = flatten_segments_to_word_speaker_pairs(ref_diar)
        hyp_pairs = flatten_segments_to_word_speaker_pairs(hyp_diar)

        if ref_pairs and hyp_pairs:
            ref_text = " ".join(word for word, _ in ref_pairs)
            hyp_text = " ".join(word for word, _ in hyp_pairs)

            alignment_result = jiwer.process_words(
                ref_text,
                hyp_text,
                reference_transform=jiwer_transform,
                hypothesis_transform=jiwer_transform,
            )

            speaker_mapping = find_optimal_speaker_mapping(ref_pairs, hyp_pairs, alignment_result)

    parts = []
    for seg in segments:
        text = seg["text"].strip()
        if text:
            speaker = seg["speaker"]
            mapped_speaker = speaker_mapping.get(speaker, speaker) if speaker_mapping else speaker
            normalized_text = normalise_text(text)
            if normalized_text:
                parts.append(f"[{mapped_speaker}] {normalized_text}")
    return " ".join(parts)


def _segments_to_diarization_format(
    segments: list[DialogueEntry] | list[SegmentDict],
) -> list[DiarizationSegment]:
    """
    Convert segments to diarization format, using dummy timing if not available.
    """
    result: list[DiarizationSegment] = []
    for seg in segments:
        if "start_time" in seg:
            seg_with_timing = cast(DialogueEntry, seg)
            start = seg_with_timing["start_time"]
            end = seg_with_timing["end_time"]
        else:
            start = 0.0
            end = 0.0
        result.append(
            {
                "speaker": seg["speaker"],
                "text": seg["text"],
                "start": start,
                "end": end,
            }
        )
    return result


def convert_segments_to_diarization_format(
    segments: list[DialogueEntry] | list[SegmentWithTiming],
) -> list[DiarizationSegment]:
    """
    Convert segments to standardized diarization format with speaker, text, start, and end.
    """
    return [
        {
            "speaker": seg["speaker"],
            "text": seg["text"],
            "start": seg["start_time"],
            "end": seg["end_time"],
        }
        for seg in segments
    ]


def calculate_speaker_count_accuracy(_rows: list[SampleRow]) -> float:
    """
    Calculate speaker count accuracy from rows with speaker_count_deviation metrics.
    """
    return 0.0

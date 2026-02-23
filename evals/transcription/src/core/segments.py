from collections.abc import Sequence
from typing import TypedDict

import jiwer

from evals.transcription.src.core.metrics.diarization import (
    find_optimal_speaker_mapping,
    flatten_segments_to_word_speaker_pairs,
)
from evals.transcription.src.core.metrics.transforms import jiwer_transform, normalise_text
from evals.transcription.src.models import DiarizationSegment, SegmentLike


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
    segments: Sequence[SegmentLike],
    reference_segments: Sequence[SegmentLike] | None = None,
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
        ref_diar = convert_to_diarization_format(reference_segments)
        hyp_diar = convert_to_diarization_format(segments)

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


def convert_to_diarization_format(segments: Sequence) -> list[DiarizationSegment]:
    """
    Convert segments to standardized diarization format with speaker, text, start, and end.
    Handles dict-like objects and objects with attributes.
    """
    result: list[DiarizationSegment] = []
    for seg in segments:
        if isinstance(seg, dict):
            result.append(
                {
                    "speaker": seg.get("speaker", ""),
                    "text": seg.get("text", ""),
                    "start": float(seg.get("start", 0.0) or seg.get("start_time", 0.0)),
                    "end": float(seg.get("end", 0.0) or seg.get("end_time", 0.0)),
                }
            )
        else:
            result.append(
                {
                    "speaker": getattr(seg, "speaker", ""),
                    "text": getattr(seg, "text", ""),
                    "start": float(getattr(seg, "start", 0.0) or getattr(seg, "start_time", 0.0)),
                    "end": float(getattr(seg, "end", 0.0) or getattr(seg, "end_time", 0.0)),
                }
            )
    return result

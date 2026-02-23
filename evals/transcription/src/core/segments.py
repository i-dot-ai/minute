from collections.abc import Sequence
from typing import TypedDict

from evals.transcription.src.models import DiarizationSegment


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

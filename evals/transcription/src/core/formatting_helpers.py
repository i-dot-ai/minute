from common.database.postgres_models import DialogueEntry
from evals.transcription.src.core.metrics.diarization import (
    find_optimal_speaker_mapping,
    flatten_segments_to_word_speaker_pairs,
)
from evals.transcription.src.core.metrics.transforms import jiwer_transform, normalise_text
from evals.transcription.src.models import DiarizationSegment


class SegmentDict:
    speaker: str
    text: str


def format_segments_with_speakers(
    segments: list[DialogueEntry] | list[dict],
    reference_segments: list[DialogueEntry] | list[dict] | None = None,
) -> str:
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

            import jiwer

            alignment_result = jiwer.process_words(
                ref_text,
                hyp_text,
                reference_transform=jiwer_transform,
                hypothesis_transform=jiwer_transform,
            )

            speaker_mapping = find_optimal_speaker_mapping(ref_pairs, hyp_pairs, alignment_result)

    parts = []
    for seg in segments:
        text = seg.get("text", "").strip() if isinstance(seg, dict) else seg["text"].strip()
        if text:
            speaker = seg.get("speaker", "") if isinstance(seg, dict) else seg["speaker"]
            mapped_speaker = speaker_mapping.get(speaker, speaker) if speaker_mapping else speaker
            normalized_text = normalise_text(text)
            if normalized_text:
                parts.append(f"[{mapped_speaker}] {normalized_text}")
    return " ".join(parts)


def _segments_to_diarization_format(
    segments: list[DialogueEntry] | list[dict],
) -> list[DiarizationSegment]:
    result: list[DiarizationSegment] = []
    for seg in segments:
        if isinstance(seg, dict):
            start = float(seg.get("start", 0.0) or 0.0)  # type: ignore[arg-type]
            end = float(seg.get("end", 0.0) or 0.0)  # type: ignore[arg-type]
            speaker = str(seg.get("speaker", ""))
            text = str(seg.get("text", ""))
        else:
            start = float(seg.get("start_time", 0.0) or 0.0)
            end = float(seg.get("end_time", 0.0) or 0.0)
            speaker = str(seg["speaker"])
            text = str(seg["text"])

        result.append(
            {
                "speaker": speaker,
                "text": text,
                "start": start,
                "end": end,
            }
        )
    return result

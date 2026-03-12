from evals.transcription.src.models import DiarizationSegment


def compute_speaker_count_metrics(
    ref_segments: list[DiarizationSegment],
    hyp_segments: list[DiarizationSegment],
) -> dict[str, int | float]:
    ref_speakers = {seg["speaker"] for seg in ref_segments} if ref_segments else set()
    hyp_speakers = {seg["speaker"] for seg in hyp_segments} if hyp_segments else set()

    ref_count = len(ref_speakers)
    hyp_count = len(hyp_speakers)
    absolute_error = abs(hyp_count - ref_count)

    is_accurate = absolute_error == 0

    return {
        "ref_speaker_count": int(ref_count),
        "hyp_speaker_count": int(hyp_count),
        "absolute_error": int(absolute_error),
        "speaker_count_accuracy": float(1.0 if is_accurate else 0.0),
    }

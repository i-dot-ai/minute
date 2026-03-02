from collections import defaultdict
from collections.abc import Generator
from typing import TypedDict

import jiwer
import numpy as np
from scipy.optimize import linear_sum_assignment

from evals.transcription.src.core.metrics.transforms import jiwer_transform
from evals.transcription.src.models import DiarizationSegment


class WDERMetrics(TypedDict):
    wder: float
    speaker_errors: int
    total_words: int


def _iterate_aligned_equal_chunks(
    ref_pairs: list[tuple[str, str]],
    hyp_pairs: list[tuple[str, str]],
    alignment_result: jiwer.WordOutput,
) -> Generator[tuple[tuple[str, str], tuple[str, str]], None, None]:
    """
    Iterate through aligned equal chunks, yielding matched reference and hypothesis pairs.
    """
    for alignment in alignment_result.alignments:
        for chunk in alignment:
            if chunk.type != "equal":
                # Skip substitutions, deletions, and insertions (already captured by WER)
                continue

            ref_slice = ref_pairs[chunk.ref_start_idx : chunk.ref_end_idx]
            hyp_slice = hyp_pairs[chunk.hyp_start_idx : chunk.hyp_start_idx + len(ref_slice)]

            yield from zip(ref_slice, hyp_slice, strict=False)


def find_optimal_speaker_mapping(
    ref_pairs: list[tuple[str, str]],
    hyp_pairs: list[tuple[str, str]],
    alignment_result: jiwer.WordOutput,
) -> dict[str, str]:
    """
    Find optimal mapping from hypothesis speakers to reference speakers.
    Uses word overlap in aligned segments to determine best speaker correspondence.

    Hypothesis speakers with no overlap are marked as UNMAPPED.
    Reference speakers with no mapping indicate missed speakers.
    """
    overlap_counts: dict[tuple[str, str], int] = defaultdict(int)

    for (_, ref_speaker), (_, hyp_speaker) in _iterate_aligned_equal_chunks(ref_pairs, hyp_pairs, alignment_result):
        overlap_counts[(hyp_speaker, ref_speaker)] += 1

    hyp_speakers = sorted({speaker for _, speaker in hyp_pairs})
    ref_speakers = sorted({speaker for _, speaker in ref_pairs})

    if not hyp_speakers or not ref_speakers:
        return {hyp_spk: f"UNMAPPED_{hyp_spk}" for hyp_spk in hyp_speakers}

    cost_matrix = np.zeros((len(hyp_speakers), len(ref_speakers)))
    for i, hyp_spk in enumerate(hyp_speakers):
        for j, ref_spk in enumerate(ref_speakers):
            cost_matrix[i, j] = overlap_counts.get((hyp_spk, ref_spk), 0)

    row_ind, col_ind = linear_sum_assignment(cost_matrix, maximize=True)

    mapping: dict[str, str] = {}
    for i, j in zip(row_ind, col_ind, strict=False):
        if cost_matrix[i, j] > 0:
            mapping[hyp_speakers[i]] = ref_speakers[j]

    for hyp_spk in hyp_speakers:
        if hyp_spk not in mapping:
            mapping[hyp_spk] = f"UNMAPPED_{hyp_spk}"

    return mapping


def flatten_segments_to_word_speaker_pairs(
    segments: list[DiarizationSegment],
) -> list[tuple[str, str]]:
    """
    Convert diarization segments into word-speaker pairs.

    Splits segment text into words, applies text transformations,
    and creates tuples of (word, speaker) for each word.
    """
    pairs: list[tuple[str, str]] = []
    for segment in segments:
        speaker = segment["speaker"]
        words = segment["text"].split()

        for word in words:
            transformed_list = jiwer_transform([word])
            if transformed_list and transformed_list[0]:
                transformed_word = transformed_list[0][0]
                pairs.append((transformed_word, speaker))

    return pairs


def compute_wder(
    ref_segments: list[DiarizationSegment],
    hyp_segments: list[DiarizationSegment],
) -> WDERMetrics:
    """
    Compute Word Diarization Error Rate (WDER) between reference and hypothesis.

    WDER measures speaker assignment errors on correctly transcribed words.
    Uses optimal speaker mapping based on word overlap to align hypothesis
    speakers with reference speakers before computing errors.
    """
    ref_pairs = flatten_segments_to_word_speaker_pairs(ref_segments)
    hyp_pairs = flatten_segments_to_word_speaker_pairs(hyp_segments)

    total_ref_words = len(ref_pairs)
    if total_ref_words == 0 or len(hyp_pairs) == 0:
        return {"wder": 0.0, "speaker_errors": 0, "total_words": total_ref_words}

    ref_text = " ".join(word for word, _ in ref_pairs)
    hyp_text = " ".join(word for word, _ in hyp_pairs)

    alignment_result = jiwer.process_words(
        ref_text,
        hyp_text,
        reference_transform=jiwer_transform,
        hypothesis_transform=jiwer_transform,
    )

    speaker_mapping = find_optimal_speaker_mapping(ref_pairs, hyp_pairs, alignment_result)

    hyp_pairs_remapped = [(word, speaker_mapping.get(speaker, speaker)) for word, speaker in hyp_pairs]

    errors = 0

    for (_, ref_speaker), (_, hyp_speaker) in _iterate_aligned_equal_chunks(
        ref_pairs, hyp_pairs_remapped, alignment_result
    ):
        if hyp_speaker != ref_speaker:
            errors += 1

    return {
        "wder": errors / total_ref_words,
        "speaker_errors": int(errors),
        "total_words": int(total_ref_words),
    }

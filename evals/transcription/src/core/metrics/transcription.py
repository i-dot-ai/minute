import jiwer

from evals.transcription.src.core.metrics.transforms import jiwer_transform
from evals.transcription.src.models import SampleMetrics


def compute_wer_metrics(refs: list[str], hyps: list[str]) -> SampleMetrics:
    """
    Computes WER and related metrics using jiwer.
    """
    word_output = jiwer.process_words(
        refs,
        hyps,
        reference_transform=jiwer_transform,
        hypothesis_transform=jiwer_transform,
    )

    return SampleMetrics(
        wer=float(word_output.wer),
        hits=int(word_output.hits),
        substitutions=int(word_output.substitutions),
        deletions=int(word_output.deletions),
        insertions=int(word_output.insertions),
        wder=0.0,
        speaker_errors=0,
        total_words=0,
        speaker_count_accuracy=0.0,
        ref_speaker_count=0,
        hyp_speaker_count=0,
    )

import jiwer

from evals.transcription.src.models import Metrics

_jiwer_transform = jiwer.Compose(
    [
        jiwer.ToLowerCase(),
        jiwer.RemoveWhiteSpace(replace_by_space=True),
        jiwer.RemoveMultipleSpaces(),
        jiwer.RemovePunctuation(),
        jiwer.ReduceToListOfListOfWords(),
    ]
)


def normalise_text(text: str) -> str:
    """
    Normalises text for WER computation by applying the same transformations as jiwer.
    """
    if not text:
        return ""
    result = _jiwer_transform(text)
    if isinstance(result, list) and len(result) > 0:
        return " ".join(result[0]) if isinstance(result[0], list) else " ".join(result)
    return ""


def compute_wer_metrics(refs: list[str], hyps: list[str]) -> Metrics:
    """
    Computes WER and related metrics using jiwer.
    """
    word_output = jiwer.process_words(
        refs,
        hyps,
        reference_transform=_jiwer_transform,
        hypothesis_transform=_jiwer_transform,
    )

    return Metrics(
        wer=float(word_output.wer),
        hits=int(word_output.hits),
        substitutions=int(word_output.substitutions),
        deletions=int(word_output.deletions),
        insertions=int(word_output.insertions),
    )

from evals.transcription.src.core.metrics.transforms import jiwer_transform


def compute_jaccard_wer(refs: list[str], hyps: list[str]) -> dict:
    if not refs or not hyps:
        return {"jaccard_wer": 0.0}

    ref_words = jiwer_transform(refs)
    hyp_words = jiwer_transform(hyps)

    ref_words_set = {word for sentence in ref_words for word in sentence}
    hyp_words_set = {word for sentence in hyp_words for word in sentence}

    intersection = len(ref_words_set & hyp_words_set)
    union = len(ref_words_set | hyp_words_set)

    jaccard_similarity = intersection / union if union > 0 else 0.0

    return {"jaccard_wer": 1.0 - jaccard_similarity}

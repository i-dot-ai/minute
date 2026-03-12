import jiwer

jiwer_transform = jiwer.Compose(
    [
        jiwer.ToLowerCase(),
        jiwer.RemoveWhiteSpace(replace_by_space=True),
        jiwer.RemoveMultipleSpaces(),
        jiwer.RemovePunctuation(),
        jiwer.ReduceToListOfListOfWords(),
    ]
)


def normalise_text(text: str) -> str:
    """Normalize text using jiwer transforms."""
    if not text:
        return ""
    result = jiwer_transform([text])
    if not result or not result[0]:
        return ""
    return " ".join(result[0])

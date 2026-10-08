import re

from breame.spelling import american_spelling_exists, get_british_spelling

from common.database.postgres_models import DialogueEntry
from common.settings import get_structured_logger

slogger = get_structured_logger()

# The pattern must start with the letter class so that positions with no following
# letters fail in O(1). A lazy non-letter prefix group re-expands to the end of the
# string at every position of a trailing non-letter run (e.g. a markdown table),
# making the scan quadratic and effectively hanging on large documents.
WORD_PATTERN = re.compile(r"[a-zA-Z]+")


def _is_ascii_letter(char: str) -> bool:
    return "a" <= char <= "z" or "A" <= char <= "Z"


def _preceded_by_backtick(text: str, word_start: int) -> bool:
    # Look for a backtick in the run of non-letter characters before the word,
    # e.g. the opening fence of a code span
    i = word_start - 1
    while i >= 0 and not _is_ascii_letter(text[i]):
        if text[i] == "`":
            return True
        i -= 1
    return False


def convert_american_to_british_spelling(  # noqa: C901
    text: str, strict: bool = False
) -> str:
    if not text.strip():
        return text

    try:

        def replace_word(match: re.Match) -> str:
            word = match.group(0)

            if not american_spelling_exists(word.lower()):
                return word

            # Skip if within code blocks
            if _preceded_by_backtick(text, match.start()):
                return word

            try:
                british = get_british_spelling(word.lower())
                # Preserve capitalization
                if word.isupper():
                    british = british.upper()
                elif word.istitle():
                    british = british.title()
                return british
            except Exception as e:
                slogger.debug("Failed to convert word {word}: {error}", word=word, error=str(e))
                if strict:
                    raise
            return word

        return WORD_PATTERN.sub(replace_word, text)

    except Exception:
        slogger.exception("Spelling conversion failed")
        if strict:
            raise
        return text


def transcript_as_speaker_and_utterance(transcript: list[DialogueEntry]) -> str:
    return "\n".join([f"{item['speaker']}: {item['text']}" for item in transcript])


def transcript_as_index_speaker_and_utterance(transcript: list[DialogueEntry]) -> str:
    return "\n".join(f"[{i}] {entry['speaker']}: {entry['text']}" for i, entry in enumerate(transcript))

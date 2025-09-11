import logging
import re
from functools import lru_cache

from breame.spelling import american_spelling_exists, get_british_spelling
from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger(__name__)


class MinuteTextProcessingSettings(BaseSettings):
    """
    Encapsulates settings for text processing related to minute transcripts.

    This class is a configuration holder to define specific thresholds for
    processing transcript texts, particularly focusing on word count
    requirements for generating summaries. These values help to guard against
    hallucinations.

    Attributes:
        MIN_WORD_COUNT_FOR_SUMMARY (int): Minimum word count required for a transcript
            to be eligible for the summary stage.
        MIN_WORD_COUNT_FOR_FULL_SUMMARY (int): Minimum word count required
            for a transcript to be eligible for the complex summary stage (i.e. a
            more elaborate prompt.
    """

    #: transcript must have at least this many words to be passed to summary stage
    MIN_WORD_COUNT_FOR_SUMMARY: int = 200
    #: transcript must have at least this many words to be passed to complex summary stage. Note, this is
    # disabled by default as is lower than the MIN_WORD_COUNT_FOR_SUMMARY
    MIN_WORD_COUNT_FOR_FULL_SUMMARY: int = 199
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


@lru_cache
def get_settings() -> MinuteTextProcessingSettings:
    return MinuteTextProcessingSettings()


def convert_american_to_british_spelling(  # noqa: C901
    text: str, strict: bool = False
) -> str:
    if not text.strip():
        return text

    try:

        def replace_word(match):
            # The first group contains any leading punctuation/spaces
            # The second group contains the word
            # The third group contains any trailing punctuation/spaces
            pre, word, post = match.groups()

            # Skip if within code blocks
            if "`" in pre or "`" in post:
                return match.group(0)

            if american_spelling_exists(word.lower()):
                try:
                    british = get_british_spelling(word.lower())
                    # Preserve capitalization
                    if word.isupper():
                        british = british.upper()
                    elif word.istitle():
                        british = british.title()
                    return pre + british + post
                except Exception as e:
                    logger.warning("Failed to convert word '%s': %s", word, e)
                    if strict:
                        raise
            return match.group(0)

        # Match any word surrounded by non-letter characters
        # Group 1: Leading non-letters (including empty)
        # Group 2: The word itself (only letters)
        # Group 3: Trailing non-letters (including empty)
        pattern = r"([^a-zA-Z]*?)([a-zA-Z]+)([^a-zA-Z]*?)"
        return re.sub(pattern, replace_word, text)

    except Exception:
        logger.exception("Failed to convert text")
        if strict:
            raise
        return text

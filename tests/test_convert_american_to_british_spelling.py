# ruff: noqa: S101
import time

from common.convert_american_to_british_spelling import convert_american_to_british_spelling

# Same code path, different strings: one table beats one test per sentence.
CASES = [
    ("The color of the theater is beautiful.", "The colour of the theatre is beautiful."),
    (
        "What color is it? The theater, as we know it, is gray.",
        "What colour is it? The theatre, as we know it, is grey.",
    ),
    ("The color of the house is red.", "The colour of the house is red."),
    (
        "The theater was crowded! The colors were bright. Was it gray?",
        "The theatre was crowded! The colours were bright. Was it grey?",
    ),
    ("The cat sat on the mat.", "The cat sat on the mat."),
    ("The color of my xyzabc is gray", "The colour of my xyzabc is grey"),
    ("xyzabc pdqrst", "xyzabc pdqrst"),
    ("XyZaBc", "XyZaBc"),
    ("Is this color xyzabc? The theater has qwerty!", "Is this colour xyzabc? The theatre has qwerty!"),
    ("| color | theater |\n|---|---|\n| 1.23 | 4,567 |", "| colour | theatre |\n|---|---|\n| 1.23 | 4,567 |"),
    ("Color", "Colour"),
    ("COLOR", "COLOUR"),
    ("color", "colour"),
    ("", ""),
]

MARKDOWN_CASES = [
    # Code blocks and inline code are left alone.
    ("```color = 'red'```", "```color = 'red'```"),
    ("Use `color = 'red'` here", "Use `color = 'red'` here"),
    # Emphasis and lists are converted.
    ("*color* and **theater**", "*colour* and **theatre**"),
    ("* color\n* theater", "* colour\n* theatre"),
]


def test_converts_expected_cases():
    for american, british in CASES:
        assert convert_american_to_british_spelling(american) == british, american


def test_markdown_syntax():
    for input_text, expected in MARKDOWN_CASES:
        assert convert_american_to_british_spelling(input_text) == expected, input_text


def test_large_trailing_non_letter_run_is_fast():
    """Regression test: a long trailing run of non-letter characters (e.g. a numeric
    markdown table) caused quadratic regex backtracking that hung the worker."""
    text = "The color is gray. " + "| 123 | 4.56 | 789 |\n" * 2500  # ~50KB non-letter tail
    start = time.perf_counter()
    result = convert_american_to_british_spelling(text)
    assert time.perf_counter() - start < 5
    assert result.startswith("The colour is grey. ")

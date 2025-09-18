# ruff: noqa: S101
from common.convert_american_to_british_spelling import convert_american_to_british_spelling


def test_basic_word_conversion():
    """Test basic American to British word conversion."""
    text = "The color of the theater is beautiful."
    expected = "The colour of the theatre is beautiful."
    assert convert_american_to_british_spelling(text) == expected


def test_preserves_capitalization():
    """Test that capitalization is preserved during conversion."""
    test_cases = [
        ("Color", "Colour"),  # Title case
        ("COLOR", "COLOUR"),  # Upper case
        ("color", "colour"),  # Lower case
    ]
    for american, british in test_cases:
        assert convert_american_to_british_spelling(american) == british


def test_punctuation_handling():
    """Test that punctuation and spacing are handled correctly."""
    text = "What color is it? The theater, as we know it, is gray."
    expected = "What colour is it? The theatre, as we know it, is grey."
    assert convert_american_to_british_spelling(text) == expected


def test_mixed_content():
    """Test text with both American and non-American words."""
    text = "The color of the house is red."
    expected = "The colour of the house is red."
    assert convert_american_to_british_spelling(text) == expected


def test_empty_string():
    """Test handling of empty string."""
    assert convert_american_to_british_spelling("") == ""


def test_multiple_sentences():
    """Test handling of multiple sentences with various punctuation."""
    text = "The theater was crowded! The colors were bright. Was it gray?"
    expected = "The theatre was crowded! The colours were bright. Was it grey?"
    assert convert_american_to_british_spelling(text) == expected


def test_no_convertible_words():
    """Test text with no American spellings."""
    text = "The cat sat on the mat."
    assert convert_american_to_british_spelling(text) == text


def test_valid_and_invalid_words():
    """Test handling of both valid American words and invalid/non-English words."""
    # Test mix of valid American words and invalid words
    text = "The color of my xyzabc is gray"
    expected = "The colour of my xyzabc is grey"
    assert convert_american_to_british_spelling(text) == expected

    # Test string with only invalid words
    text = "xyzabc pdqrst"
    assert convert_american_to_british_spelling(text) == text

    # Test mixed case invalid words
    text = "XyZaBc"
    assert convert_american_to_british_spelling(text) == text


def test_mixed_valid_invalid_with_punctuation():
    """Test handling of valid and invalid words with punctuation."""
    text = "Is this color xyzabc? The theater has qwerty!"
    expected = "Is this colour xyzabc? The theatre has qwerty!"
    assert convert_american_to_british_spelling(text) == expected


def test_markdown_syntax():
    """Test that markdown syntax is preserved."""
    test_cases = [
        # Code blocks
        ("```color = 'red'```", "```color = 'red'```"),
        # Inline code
        ("Use `color = 'red'` here", "Use `color = 'red'` here"),
        # Links
        # (
        #     "[color guide](http://example.com/color)",
        #     "[colour guide](http://example.com/color)",
        # ),
        # Emphasis
        ("*color* and **theater**", "*colour* and **theatre**"),
        # Lists
        ("* color\n* theater", "* colour\n* theatre"),
    ]
    for input_text, expected in test_cases:
        assert convert_american_to_british_spelling(input_text) == expected

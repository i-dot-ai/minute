_WAF_TRANSLATION_TABLE = str.maketrans("-\u2013\u2014", "   ", "<>*;={}()`~|")


def sanitize_for_waf(text: str) -> str:
    """Removes characters that trigger Azure WAF False Positives."""
    return text.translate(_WAF_TRANSLATION_TABLE)

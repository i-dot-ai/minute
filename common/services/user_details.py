import re

_LOCAL_PART_SEPARATORS = re.compile(r"[._]+")


def display_name_from_email(email: str) -> str:
    """Derive a fallback display name from an email's local part ("jane.o.smith-2@…" -> "Jane Smith").

    Hyphenated surnames glue ("jane.smith-jones@…" -> "Jane Smith-Jones") and mailbox
    counter numbers are dropped ("jane.smith3@…" -> "Jane Smith"). Read-time fallback
    only for users with no stored name; the derived value is never persisted.
    """
    local_part = email.split("@", maxsplit=1)[0]
    usable = local_part.split("+", maxsplit=1)[0]

    def without_mailbox_counter(segment: str) -> str:
        # Trailing digits are mailbox counters (jane.smith3); digits inside a
        # segment (ab12cd) are part of the name and kept.
        return re.sub(r"[-\d]+$", "", segment)

    tokens = [without_mailbox_counter(segment) for segment in _LOCAL_PART_SEPARATORS.split(usable)]
    tokens = [token for token in tokens if token]
    if not tokens:
        return local_part

    selected = [tokens[0], tokens[-1]] if len(tokens) > 1 else tokens[:1]
    return " ".join("-".join(part.capitalize() for part in word.split("-")) for word in selected)

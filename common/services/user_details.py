import re

_LOCAL_PART_SEPARATORS = re.compile(r"[._-]+")


def display_name_from_email(email: str) -> str:
    """Derive a fallback display name from an email's local part ("jane.o.smith-2@…" -> "Jane Smith").

    Read-time fallback only for users with no stored name; the derived value is never persisted.
    """
    local_part = email.split("@", maxsplit=1)[0]
    usable = local_part.split("+", maxsplit=1)[0]
    parts = [part for part in _LOCAL_PART_SEPARATORS.split(usable) if part and any(c.isalpha() for c in part)]
    words = [parts[0], parts[-1]] if len(parts) > 1 else parts[:1]
    return " ".join(word.capitalize() for word in words) if words else local_part

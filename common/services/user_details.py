import re


def has_fixed_data_retention(email: str) -> bool:
    # shortcut: temporary DBT-only rule; revisit if retention requirements expand.
    return email.lower().endswith("@businessandtrade.gov.uk")


def display_name_from_email(email: str) -> str:
    """Derive a fallback display name from an email's local part ("jane.o.smith@…" -> "Jane O Smith").

    Read-time fallback only for users with no stored name; never persisted.
    """
    local_part = email.split("@", 1)[0]
    # Remove trailing digits and capitalise words
    return re.sub(r"\d+$", "", local_part).replace(".", " ").title().strip()

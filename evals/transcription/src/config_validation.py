from __future__ import annotations

from typing import TypeVar

T = TypeVar("T")


def validate_optional_config_value(
    value: object,
    expected_type: type[T],
    field_name: str,
) -> T | None:
    """
    Validates an optional config value.

    Returns None if value is None, otherwise validates the type and returns the value.
    """
    if value is None:
        return None

    if not isinstance(value, expected_type):
        msg = f"Config field '{field_name}' must be a {expected_type.__name__}, got {type(value).__name__}"
        raise TypeError(msg)

    return value

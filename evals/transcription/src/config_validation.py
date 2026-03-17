from __future__ import annotations

from typing import TypeVar

T = TypeVar("T")


def get_config(
    config: dict[str, object], key: str, expected_type: type[T], *, default: T | None = None, required: bool = False
) -> T | None:
    value = config.get(key)

    if value is None:
        if required:
            msg = f"Required config field '{key}' is missing"
            raise ValueError(msg)
        return default

    if not isinstance(value, expected_type):
        msg = f"Config field '{key}' must be a {expected_type.__name__}, got {type(value).__name__}"
        raise TypeError(msg)

    return value

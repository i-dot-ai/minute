from __future__ import annotations

import pytest

from evals.transcription.src.config_validation import validate_optional_config_value


def test_validate_optional_config_value_returns_none_when_value_is_none() -> None:
    result = validate_optional_config_value(None, int, "test_field")
    assert result is None


def test_validate_optional_config_value_returns_value_when_type_matches() -> None:
    result = validate_optional_config_value(42, int, "test_field")
    assert result == 42


def test_validate_optional_config_value_raises_type_error_when_type_mismatches() -> None:
    with pytest.raises(TypeError, match="Config field 'test_field' must be a int, got str"):
        validate_optional_config_value("not an int", int, "test_field")


def test_validate_optional_config_value_works_with_float() -> None:
    result = validate_optional_config_value(3.14, float, "test_field")
    assert result == 3.14


def test_validate_optional_config_value_works_with_bool() -> None:
    result = validate_optional_config_value(True, bool, "test_field")
    assert result is True


def test_validate_optional_config_value_works_with_str() -> None:
    result = validate_optional_config_value("hello", str, "test_field")
    assert result == "hello"


def test_validate_optional_config_value_works_with_list() -> None:
    result = validate_optional_config_value([1, 2, 3], list, "test_field")
    assert result == [1, 2, 3]

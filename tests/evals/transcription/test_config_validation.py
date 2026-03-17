from __future__ import annotations

import pytest

from evals.transcription.src.config_validation import get_config


def test_get_config_returns_none_when_value_is_missing() -> None:
    result = get_config({}, "test_field", int)
    assert result is None


def test_get_config_returns_value_when_type_matches() -> None:
    result = get_config({"test_field": 42}, "test_field", int)
    assert result == 42


def test_get_config_raises_type_error_when_type_mismatches() -> None:
    with pytest.raises(TypeError, match="Config field 'test_field' must be a int, got str"):
        get_config({"test_field": "not an int"}, "test_field", int)


def test_get_config_works_with_float() -> None:
    result = get_config({"test_field": 3.14}, "test_field", float)
    assert result == 3.14


def test_get_config_works_with_bool() -> None:
    result = get_config({"test_field": True}, "test_field", bool)
    assert result is True


def test_get_config_works_with_str() -> None:
    result = get_config({"test_field": "hello"}, "test_field", str)
    assert result == "hello"


def test_get_config_works_with_list() -> None:
    result = get_config({"test_field": [1, 2, 3]}, "test_field", list)
    assert result == [1, 2, 3]


def test_get_config_returns_default_when_missing() -> None:
    result = get_config({}, "test_field", bool, default=False)
    assert result is False


def test_get_config_raises_when_required_and_missing() -> None:
    with pytest.raises(ValueError, match="Required config field 'test_field' is missing"):
        get_config({}, "test_field", str, required=True)

import pytest
from pydantic import ValidationError

from common.settings import Settings, get_settings


def test_default_lease_timings_are_ordered():
    settings = get_settings()
    assert settings.JOB_HEARTBEAT_INTERVAL_SECS < settings.JOB_VISIBILITY_TIMEOUT_SECS < settings.JOB_STALE_SECONDS


def test_lease_timings_must_be_strictly_ordered():
    # heartbeat must be < visibility < stale; an equal/reversed pair must not construct.
    with pytest.raises(ValidationError, match="JOB_HEARTBEAT_INTERVAL_SECS"):
        Settings(  # type: ignore[call-arg]  # required fields come from the env, as in get_settings()
            JOB_HEARTBEAT_INTERVAL_SECS=120,
            JOB_VISIBILITY_TIMEOUT_SECS=60,
            JOB_STALE_SECONDS=120,
        )

import logging
from typing import Any

import sentry_sdk
from sentry_sdk.integrations.logging import LoggingIntegration

from common.settings import get_settings

settings = get_settings()


def init_sentry() -> None:
    """Initialise Sentry.

    Safe to call multiple times and from multiple processes (e.g. each Ray
    actor runs in its own process and must initialise Sentry independently).
    """
    if settings.SENTRY_DSN is None:
        return

    sentry_init_opts: dict[str, Any]
    if settings.ENVIRONMENT == "prod":
        sentry_init_opts = {
            "traces_sample_rate": 1.0,
            "profile_session_sample_rate": 0.2,
        }
    else:
        sentry_init_opts = {
            "send_default_pii": True,
            "traces_sample_rate": 1.0,
            "profile_session_sample_rate": 1.0,
            "profile_lifecycle": "trace",
        }
    sentry_sdk.init(
        dsn=settings.SENTRY_DSN,
        environment=settings.ENVIRONMENT,
        release=settings.SENTRY_RELEASE,
        enable_logs=True,
        integrations=[
            # Forward all app log records (INFO and above) to Sentry Logs.
            LoggingIntegration(sentry_logs_level=logging.INFO),
        ],
        **sentry_init_opts,
    )

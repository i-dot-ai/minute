import logging
from typing import Any

import sentry_sdk

from common.settings import get_settings

logger = logging.getLogger(__name__)


def init_sentry() -> None:
    """Initialise Sentry for a worker process, if a DSN is configured.

    Mirrors the backend's initialisation so worker performance transactions
    (e.g. the Azure transcription spans) and errors are reported. A no-op when
    SENTRY_DSN is unset (e.g. local development).
    """
    settings = get_settings()
    if not settings.SENTRY_DSN:
        return

    sentry_init_opts: dict[str, Any]
    if settings.ENVIRONMENT == "prod":
        sentry_init_opts = {
            "traces_sample_rate": 1.0,
            "profile_session_sample_rate": 0.2
        }
    else:
        sentry_init_opts = {
            "send_default_pii": True,
            "traces_sample_rate": 1.0,
            "profile_session_sample_rate": 1.0,
            "profile_lifecycle": "trace",
        }

    sentry_sdk.init(settings.SENTRY_DSN, environment=settings.ENVIRONMENT, **sentry_init_opts)
    logger.info("Sentry initialised for worker (environment=%s)", settings.ENVIRONMENT)

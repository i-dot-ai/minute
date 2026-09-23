import logging
from typing import Any

import sentry_sdk

from common.settings import get_settings

logger = logging.getLogger(__name__)


def init_sentry() -> None:
    """Initialise Sentry for a worker process.

    Mirrors the backend's initialisation so worker performance transactions
    (e.g. the Azure transcription spans) and errors are reported.

    Two modes:
      - Production/dev: reports to Sentry cloud when SENTRY_DSN is set.
      - Local: when ENVIRONMENT == "local" we enable Spotlight, which streams
        events to a local sidecar (see docker-compose `spotlight` service) so you
        can inspect traces/perf/errors in the browser at http://localhost:8969
        with no DSN and nothing leaving your machine.

    A no-op when neither a DSN nor local Spotlight is configured.
    """
    settings = get_settings()

    is_local = settings.ENVIRONMENT.lower() == "local"
    if not settings.SENTRY_DSN and not is_local:
        return

    sentry_init_opts: dict[str, Any]
    if settings.ENVIRONMENT == "prod":
        sentry_init_opts = {
            "traces_sample_rate": 1.0,
            "profile_session_sample_rate": 0.2,
            "enable_logs": True,
        }
    else:
        sentry_init_opts = {
            "send_default_pii": True,
            "traces_sample_rate": 1.0,
            "profile_session_sample_rate": 1.0,
            "profile_lifecycle": "trace",
            "enable_logs": True,
        }

    if is_local:
        # Stream to the local Spotlight sidecar. Inside docker-compose the sidecar
        # is reachable by service name; SENTRY_SPOTLIGHT overrides the default
        # http://localhost:8969/stream for host-run processes.
        sentry_init_opts["spotlight"] = True

    # DSN may be None locally; Spotlight works without one.
    sentry_sdk.init(settings.SENTRY_DSN, environment=settings.ENVIRONMENT, **sentry_init_opts)
    logger.info("Sentry initialised for worker (environment=%s)", settings.ENVIRONMENT)


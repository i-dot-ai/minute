from typing import Any
from urllib.parse import urlsplit

import sentry_sdk

from common.settings import get_settings

settings = get_settings()


def _redact_search_query(event: dict[str, Any], hint: dict[str, Any]) -> dict[str, Any]:  # noqa: ARG001
    request = event.get("request", {})
    if urlsplit(request.get("url", "")).path == "/transcriptions/search":
        request["url"] = request["url"].partition("?")[0]
        request.pop("query_string", None)
    return event


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
        before_send=_redact_search_query,
        before_send_transaction=_redact_search_query,
        **sentry_init_opts,
    )

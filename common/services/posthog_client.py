import logging
from typing import Any
from uuid import UUID

import posthog

from common.settings import get_settings

logger = logging.getLogger(__name__)

settings = get_settings()
posthog_client = None
if settings.POSTHOG_API_KEY:
    posthog_client = posthog.Posthog(settings.POSTHOG_API_KEY, host=settings.POSTHOG_HOST)


def capture_event(
    distinct_id: UUID | str | None,
    event: str,
    properties: dict[str, Any] | None = None,
) -> None:
    """Capture a PostHog event from backend/worker code.

    No-op when PostHog is not configured (e.g. local/tests) or the user is unknown.
    Non-blocking: events are queued and sent by the client's background thread. Never
    raises: analytics must not break job processing.
    """
    if posthog_client is None or distinct_id is None:
        return
    try:
        posthog_client.capture(distinct_id=str(distinct_id), event=event, properties=properties or {})
    except Exception:
        logger.exception("Failed to capture PostHog event %s", event)

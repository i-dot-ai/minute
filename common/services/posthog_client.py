import posthog

from common.settings import get_settings

settings = get_settings()
posthog_client = None
if settings.POSTHOG_API_KEY:
    posthog_client = posthog.Posthog(settings.POSTHOG_API_KEY, host=settings.POSTHOG_HOST)

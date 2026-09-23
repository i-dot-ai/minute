import sentry_sdk

from common.settings import get_settings


def init_sentry() -> None:
    """Initialise Sentry for the current process, if a DSN is configured.

    Shared by the backend and worker so both report with the same options.
    """
    settings = get_settings()
    if not settings.SENTRY_DSN:
        return

    if settings.ENVIRONMENT == "prod":
        sentry_init_opts = {"traces_sample_rate": 1.0, "profile_session_sample_rate": 0.2}
    else:
        sentry_init_opts = {
            "send_default_pii": True,
            "traces_sample_rate": 1.0,
            "profile_session_sample_rate": 1.0,
            "profile_lifecycle": "trace",
        }
    sentry_sdk.init(settings.SENTRY_DSN, environment=settings.ENVIRONMENT, **sentry_init_opts)

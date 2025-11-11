from i_dot_ai_utilities.auth.auth_api import AuthApiClient, UserAuthorisationResult
import logging

from common.logger import setup_structured_logger
from common.settings import get_settings

settings = get_settings()
logger  = setup_structured_logger(level=settings.LOG_LEVEL)

auth_client = AuthApiClient(
    app_name=settings.REPO,
    auth_api_url=settings.AUTH_API_URL,
    logger=logger,
    timeout=settings.AUTH_API_REQUEST_TIMEOUT or 5,
)


def __load_dummy_user_info() -> UserAuthorisationResult:
    """
    Returns a dummy UserAuthorisationResult, as one would be received from the Auth API's /token/authorise endpoint.
    Used for local testing.
    """
    return UserAuthorisationResult(
        email="test@test.co.uk",
        is_authorised=True,
        auth_reason="LOCAL_TESTING",
    )


def get_user_info(auth_token: str) -> UserAuthorisationResult:
    """
    Retrieve user metadata, including the user email and whether they should have access to the app.
    """
    try:
        if settings.ENVIRONMENT == "local":
            return __load_dummy_user_info()

        return auth_client.get_user_authorisation_info(auth_token)
    except Exception:
        logger.exception("Error occurred when authorising user")
        raise


def is_authorised_user(auth_token: str) -> bool:
    """
    A simple wrapper function to call the Auth API and check the user is permitted to access the resource.
    """
    try:
        return get_user_info(auth_token).is_authorised
    except Exception:
        logger.exception("Error occurred when authorising user")
        return False

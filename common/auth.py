from i_dot_ai_utilities.auth.auth_api import AuthApiClient, UserAuthorisationResult

from common.services.exceptions import MissingAuthTokenError
from common.settings import get_settings, get_structured_logger

settings = get_settings()
logger = get_structured_logger()

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


def get_user_info(auth_token: str | None) -> UserAuthorisationResult:
    """
    Retrieve user metadata, including the user email and whether they should have access to the app.
    """
    if settings.ENVIRONMENT == "local":
        return __load_dummy_user_info()

    if not auth_token:
        raise MissingAuthTokenError

    try:
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

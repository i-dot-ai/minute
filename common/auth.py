import logging
import os

import jwt
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.asymmetric.rsa import RSAPublicKey
from cryptography.hazmat.primitives.serialization import load_pem_public_key

logger = logging.getLogger(__name__)


class AuthorisationError(Exception):
    pass


def __convert_to_pem_public_key(key_base64: str) -> RSAPublicKey:
    """
    Convert Base64 public key to PEM format.
    """
    public_key_pem = f"-----BEGIN PUBLIC KEY-----\n{key_base64}\n-----END PUBLIC KEY-----"

    return load_pem_public_key(public_key_pem.encode(), backend=default_backend())


def __get_decoded_jwt(jwt_token: str, verify_signature: bool) -> dict:
    """
    Get JWT payload, optionally validating the JWT signature against a known public key.
    """
    try:
        if verify_signature:
            public_key_encoded = os.environ.get(
                "AUTH_PROVIDER_PUBLIC_KEY"
            )  # This is passed into the environment by ECS
            pem_public_key = __convert_to_pem_public_key(public_key_encoded)
        else:
            pem_public_key = None
        return jwt.decode(
            jwt_token,
            pem_public_key,
            algorithms=["RS256"],
            audience="account",
            options={
                "verify_signature": verify_signature,
                "verify_exp": verify_signature,
            },
        )
    except jwt.ExpiredSignatureError:
        logger.info("User's authentication token has expired.")
        raise
    except jwt.InvalidTokenError:
        logger.exception("Invalid authentication token")
        raise
    except Exception as e:
        error_msg = "Unhanded decoding error"
        logger.exception(error_msg)
        raise AuthorisationError(error_msg) from e


def parse_auth_token(auth_header) -> tuple[str, list[str]]:
    """
    Takes a Keycloak JWT (auth token) as input and returns the user's email address and associated roles.
    Use this function to identify the logged-in user, and which roles they are assigned by Keycloak.
    Also validates that the token has come from Keycloak for security reasons. Validation should
    always be true unless running locally.
    """

    if auth_header is None:
        error_msg = "No auth token provided to parse."
        logger.error(error_msg)
        raise AuthorisationError(error_msg)

    verify_jwt_source = not os.environ.get("DISABLE_AUTH_SIGNATURE_VERIFICATION")
    token_content = __get_decoded_jwt(auth_header, verify_jwt_source)

    email = token_content.get("email")
    if not email:
        error_msg = "No email found in token"
        logger.error(error_msg)
        raise AuthorisationError(error_msg)

    realm_access = token_content.get("realm_access")
    if not realm_access:
        error_msg = "Realm access not found in token"
        logger.error(error_msg)
        raise AuthorisationError(error_msg)

    role_names = realm_access.get("roles")
    logger.debug("Roles for found in token for %s: %s", email, role_names)
    return email, role_names


def is_authorised_user(auth_header) -> bool:
    """
    A simple wrapper function to check if the user has the required role to access the resource.
    """
    _, roles = parse_auth_token(auth_header)

    return os.environ.get("REPO") in roles

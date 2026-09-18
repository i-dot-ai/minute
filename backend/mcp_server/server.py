"""Assembles the MCP server and its ASGI app (then mounted on the fastapi app)."""

from fastmcp import FastMCP
from fastmcp.server.auth import TokenVerifier
from fastmcp.server.auth.oidc_proxy import OIDCProxy
from fastmcp.server.http import StarletteWithLifespan

from backend.mcp_server.auth import AuthApiTokenVerifier
from backend.mcp_server.tools import get_transcript, list_transcripts
from common.settings import get_settings, get_structured_logger

settings = get_settings()
logger = get_structured_logger()

MCP_INTERNAL_PATH = "/"
INSTRUCTIONS = """Read-only access to the meeting transcripts held in Minute for the user whose token you are using.

Use list_transcripts to find a meeting, optionally narrowing by date, then get_transcript to read it.
"""


class MissingMcpOidcClientError(RuntimeError):
    """Raised when a deployed environment has no Internal Access client to use."""

    def __init__(self, environment: str) -> None:
        super().__init__(
            f"MCP is enabled in '{environment}' but MCP_OIDC_CLIENT_ID and MCP_OIDC_CLIENT_SECRET are unset. "
            "Set them or set MCP_ENABLED to `false`"
        )


def oauth_is_configured() -> bool:
    """Whether there is an Internal Access client to run the OAuth flow with."""
    return bool(settings.MCP_OIDC_CLIENT_ID and settings.MCP_OIDC_CLIENT_SECRET)


def build_auth() -> TokenVerifier | OIDCProxy:
    """The credential the endpoint accepts, and how it is checked.

    With an Internal Access client registered, the server runs the OAuth flow
    itself. The proxy keeps the Internal Access token and, on every request, swaps the
    token it issued for that one and passes it to the verifier (AuthApiTokenVerifier) so the Auth
    API is still asked "is this person allowed in Minute?" per request.

    # NOTE: have not tested with an actual registered client this OAUTH flow yet. its a WIP.
    """
    verifier = AuthApiTokenVerifier(base_url=settings.MCP_SERVER_URL)

    client_id = settings.MCP_OIDC_CLIENT_ID
    client_secret = settings.MCP_OIDC_CLIENT_SECRET
    if not (client_id and client_secret):
        if settings.ENVIRONMENT != "local":
            raise MissingMcpOidcClientError(settings.ENVIRONMENT)
        logger.info("MCP: local development, accepting a bearer token the Auth API recognises")
        return verifier

    redirect_uri = f"{settings.MCP_SERVER_URL.rstrip('/')}/auth/callback"
    logger.info(
        "Serving MCP with OAuth activated. Redirect URI: {redirect_uri}",
        redirect_uri=redirect_uri,
    )

    return OIDCProxy(
        config_url=settings.MCP_OIDC_CONFIG_URL,
        client_id=client_id,
        client_secret=client_secret,
        base_url=settings.MCP_SERVER_URL,
        valid_scopes=settings.MCP_OIDC_SCOPES,
        token_verifier=verifier,
    )


def build_mcp_server() -> FastMCP:
    return FastMCP(
        name="minute",
        instructions=INSTRUCTIONS,
        auth=build_auth(),
        tools=[list_transcripts, get_transcript],
    )


def build_mcp_app(server: FastMCP | None = None) -> StarletteWithLifespan:
    """The app to mount at /mcp."""
    return (server or build_mcp_server()).http_app(
        path=MCP_INTERNAL_PATH,
        stateless_http=True,
        host_origin_protection=False,
    )


def well_known_routes(server: FastMCP, mcp_path: str = MCP_INTERNAL_PATH) -> list:
    """The discovery documents needed for the oauth flow, to be served from the root of the parent app."""
    auth = server.auth
    if auth is None or not hasattr(auth, "get_well_known_routes"):
        return []
    return auth.get_well_known_routes(mcp_path)

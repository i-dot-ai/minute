"""Assembles the MCP server and its ASGI app.

Mounted into the FastAPI app rather than run separately, so it shares the
settings, database pool and deployment of the API it reads from.
"""

from fastmcp import FastMCP
from fastmcp.server.http import StarletteWithLifespan

from backend.mcp_server.auth import AuthApiTokenVerifier
from backend.mcp_server.tools import get_transcript, list_transcripts
from common.settings import get_settings

settings = get_settings()

INSTRUCTIONS = """Read-only access to the meeting transcripts held in Minute for the user whose token you are using.

Use list_transcripts to find a meeting, optionally narrowing by date, then get_transcript to read it.
"""


def build_mcp_server() -> FastMCP:
    return FastMCP(
        name="minute",
        instructions=INSTRUCTIONS,
        auth=AuthApiTokenVerifier(
            base_url=settings.MCP_SERVER_URL,
        ),
        tools=[list_transcripts, get_transcript],
    )


def build_mcp_app() -> StarletteWithLifespan:
    """The ASGI app to mount at /mcp.

    Stateless because the tools hold nothing between calls, so any instance
    behind the load balancer can serve any request. Host and Origin checks are
    left to the load balancer and WAF in front of us.

    An unauthenticated request is answered with a 401 pointing at this server's
    protected-resource metadata (RFC 9728). Nothing serves that document yet: a
    bare token verifier has no authorisation server to name in it. Naming the
    auth provider there is what will publish it, and that is the same change
    that makes the OAuth flow work.
    """
    return build_mcp_server().http_app(
        path="/",
        stateless_http=True,
        host_origin_protection=False,
    )

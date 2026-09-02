import contextlib
import logging
from contextlib import asynccontextmanager

import sentry_sdk
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer

from backend.api.routes import router as api_router
from backend.cleanup_job import init_cleanup_scheduler
from backend.mcp_server import build_mcp_app
from common.settings import get_settings

settings = get_settings()
log = logging.getLogger("uvicorn")

mcp_app = build_mcp_app() if settings.MCP_ENABLED else None


@asynccontextmanager
async def lifespan(app_: FastAPI):  # noqa: ARG001
    log.info("Starting up...")

    await init_cleanup_scheduler()

    async with contextlib.AsyncExitStack() as stack:
        # the exit stack guaranees an orderly cleanup when fastapi shuts down
        if mcp_app:
            await stack.enter_async_context(mcp_app.lifespan(mcp_app))
            log.info("MCP server mounted at /mcp")

        yield

    log.info("Shutting down...")


# init sentry, if used
if settings.SENTRY_DSN:
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
app = FastAPI(lifespan=lifespan, openapi_url="/api/openapi.json")


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# Configure CORS

origins = [settings.APP_URL]


app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)

if mcp_app:
    app.mount("/mcp", mcp_app)

if settings.STORAGE_SERVICE_NAME == "local":
    from common.services.storage_services.local.mock_storage_service import mock_storage_app

    log.info(
        "Using 'local' storage service. We recommend only using this for development. "
        "Uploaded files are stored in .data/",
    )
    app.mount("/mock_storage", mock_storage_app)

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8080)  # noqa: S104

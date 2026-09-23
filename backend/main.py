import logging
from contextlib import asynccontextmanager
from typing import Any

import sentry_sdk
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer

from backend.api.routes import router as api_router
from backend.cleanup_job import init_cleanup_scheduler
from common.settings import get_settings

settings = get_settings()
log = logging.getLogger("uvicorn")


@asynccontextmanager
async def lifespan(app_: FastAPI):  # noqa: ARG001
    log.info("Starting up...")

    await init_cleanup_scheduler()

    yield

    log.info("Shutting down...")


# init sentry, if used. Locally (ENVIRONMENT=local) we enable Spotlight so traces,
# perf and errors can be inspected in the browser at http://localhost:8969 with no
# DSN required (see the docker-compose `spotlight` service).
_is_local = settings.ENVIRONMENT.lower() == "local"
if settings.SENTRY_DSN or _is_local:
    sentry_init_opts: dict[str, Any]
    if settings.ENVIRONMENT == "prod":
        sentry_init_opts = {
            "traces_sample_rate": 1.0,
            "profile_session_sample_rate": 0.2,
            "enable_logs": True,
        }
    else:
        sentry_init_opts = {
            "send_default_pii": True,
            "traces_sample_rate": 1.0,
            "profile_session_sample_rate": 1.0,
            "profile_lifecycle": "trace",
            "enable_logs": True,
        }
    if _is_local:
        sentry_init_opts["spotlight"] = True
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

if settings.STORAGE_SERVICE_NAME == "local":
    from common.services.storage_services.local.mock_storage_service import mock_storage_app

    log.info(
        "Using 'local' storage service. We recommend only using this for development. "
        "Uploaded files are stored in .data/",
    )
    app.mount("/mock_storage", mock_storage_app)

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8080)  # noqa: S104

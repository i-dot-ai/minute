import logging
from typing import Annotated

from fastapi import APIRouter, HTTPException, Query

from backend.api.dependencies import UserDep
from backend.utils import temporal_status
from common.types import StatusResponse

status_router = APIRouter(tags=["Status"])
logger = logging.getLogger(__name__)
_MAX_HORIZON_SECONDS = 86_400


@status_router.get("/status", response_model=StatusResponse)
async def get_status(
    _current_user: UserDep,
    horizon: Annotated[
        str, Query(pattern=r"^[1-9][0-9]{0,3}[mh]$", description="Last 1 minute to 24 hours, e.g. 10m, 1h, 24h")
    ] = "10m",
) -> StatusResponse:
    """Aggregate workflow-run counts and nearest-rank timing percentiles in seconds.

    Starts and closures use the horizon; in-progress counts/ages include older runs.
    Processing time covers successful whole pipelines, including waiting/retries,
    not upload time or time until the transcript is ready. Completed transcription
    workflows can still have optional enrichment/summary failures. Visibility is
    eventually consistent; successful responses are cached for 30 seconds.
    """
    seconds = int(horizon[:-1]) * (60 if horizon[-1] == "m" else 3_600)
    if seconds > _MAX_HORIZON_SECONDS:
        raise HTTPException(status_code=422, detail="horizon must be between 1 minute and 24 hours")
    try:
        return await temporal_status.get_status(seconds)
    except Exception as exc:
        logger.exception("Failed to collect Temporal status")
        raise HTTPException(status_code=503, detail="Processing status is temporarily unavailable") from exc

from fastapi import APIRouter

from backend.api.routes.minutes import (
    create_minute,
    create_minute_version,
    delete_minute,
    delete_minute_version,
    get_minute,
    get_minute_version,
    list_minute_versions,
    list_minutes_for_transcription,
)
from common.database.postgres_models import Minute, MinuteVersion
from common.types import MinuteListItem, MinuteVersionResponse

router = APIRouter(tags=["Minutes"])

router.add_api_route(
    path="/transcription/{transcription_id}/minutes",
    endpoint=list_minutes_for_transcription.endpoint,
    response_model=list[MinuteListItem],
    methods=["GET"],
)

router.add_api_route(
    path="/transcription/{transcription_id}/minutes",
    endpoint=create_minute.endpoint,
    response_model=MinuteListItem,
    methods=["POST"],
)

router.add_api_route(
    path="/minutes/{minute_id}",
    endpoint=get_minute.endpoint,
    response_model=Minute,
    methods=["GET"],
)

router.add_api_route(
    path="/minutes/{minute_id}",
    endpoint=delete_minute.endpoint,
    status_code=204,
    methods=["DELETE"],
)

router.add_api_route(
    path="/minutes/{minute_id}/versions",
    endpoint=list_minute_versions.endpoint,
    response_model=list[MinuteVersionResponse],
    methods=["GET"],
)

router.add_api_route(
    path="/minutes/{minute_id}/versions",
    endpoint=create_minute_version.endpoint,
    response_model=MinuteVersionResponse,
    methods=["POST"],
)

router.add_api_route(
    path="/minute_versions/{minute_version_id}",
    endpoint=get_minute_version.endpoint,
    response_model=MinuteVersion,
    methods=["GET"],
)

router.add_api_route(
    path="/minute_versions/{minute_version_id}",
    endpoint=delete_minute_version.endpoint,
    methods=["DELETE"],
)

# Alias so existing `from .minutes import minutes_router` wiring keeps working.
minutes_router = router

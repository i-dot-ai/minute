from fastapi import APIRouter

from backend.api.routes.users import get_user, update_data_retention, update_default_template
from common.types import GetUserResponse

router = APIRouter(tags=["Users"], prefix="/users")

router.add_api_route(
    path="/me",
    endpoint=get_user.endpoint,
    response_model=GetUserResponse,
    methods=["GET"],
)

router.add_api_route(
    path="/data-retention",
    endpoint=update_data_retention.endpoint,
    response_model=GetUserResponse,
    methods=["PATCH"],
)

router.add_api_route(
    path="/default-template",
    endpoint=update_default_template.endpoint,
    response_model=GetUserResponse,
    methods=["PATCH"],
)

from uuid import UUID

from fastapi import APIRouter

from backend.api.routes.user_templates import (
    create_user_template,
    delete_user_template,
    duplicate_user_template,
    get_user_template,
    list_user_templates,
    update_user_template,
)
from common.types import TemplateResponse

router = APIRouter(tags=["Templates"], prefix="/user-templates")

router.add_api_route(
    path="",
    endpoint=list_user_templates.endpoint,
    response_model=list[TemplateResponse],
    methods=["GET"],
)

router.add_api_route(
    path="/{template_id}",
    endpoint=get_user_template.endpoint,
    response_model=TemplateResponse,
    methods=["GET"],
)

router.add_api_route(
    path="",
    endpoint=create_user_template.endpoint,
    response_model=None,
    methods=["POST"],
)

router.add_api_route(
    path="/{template_id}",
    endpoint=update_user_template.endpoint,
    response_model=None,
    methods=["PATCH"],
)

router.add_api_route(
    path="/{template_id}",
    endpoint=delete_user_template.endpoint,
    response_model=None,
    methods=["DELETE"],
)

router.add_api_route(
    path="/{template_id}/duplicate",
    endpoint=duplicate_user_template.endpoint,
    response_model=UUID,
    methods=["POST"],
)

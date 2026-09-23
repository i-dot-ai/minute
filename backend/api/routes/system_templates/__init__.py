from fastapi import APIRouter

from backend.api.routes.system_templates import get_templates
from common.types import TemplateMetadata

router = APIRouter(tags=["Templates"])

router.add_api_route(
    path="/templates",
    endpoint=get_templates.endpoint,
    response_model=list[TemplateMetadata],
    methods=["GET"],
)

from fastapi import APIRouter

from common.services import system_template_manager
from common.settings import get_settings

templates_router = APIRouter(tags=["Templates"])
all_template_metadata = system_template_manager.get_template_metadata()
beta_templates = get_settings().BETA_TEMPLATE_NAMES
ga_only_template_metadata = [template for template in all_template_metadata if template.name not in beta_templates]

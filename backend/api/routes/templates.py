from fastapi import APIRouter

from backend.api.dependencies import UserDep
from backend.app.minutes.types import (
    TemplateMetadata,
)
from backend.services.template_manager import TemplateManager
from common.settings import get_settings

templates_router = APIRouter(tags=["Templates"])
all_template_metadata = TemplateManager.get_template_metadata()
beta_templates = get_settings().BETA_TEMPLATE_NAMES
ga_only_template_metadata = [template for template in all_template_metadata if template.name not in beta_templates]


@templates_router.get("/templates")
def get_templates(user: UserDep) -> list[TemplateMetadata]:  # noqa: ARG001
    """Get metadata for all templates."""
    # currently we have no beta templates. Uncomment this code to enable this feature
    # if posthog_client and posthog_client.get_feature_flag("beta-templates", user.email):
    #     return all_template_metadata
    # else:
    #     return ga_only_template_metadata
    return ga_only_template_metadata

from backend.api.dependencies import UserDep
from common.services import system_template_manager
from common.types import TemplateMetadata


def endpoint(
    user: UserDep,
) -> list[TemplateMetadata]:
    """Get metadata for all templates."""

    return [
        template.model_copy(update={"is_default": template.name == user.default_template_name})
        for template in system_template_manager.get_template_metadata()
    ]

import logging
import typing

from common.templates.default.cabinet import Cabinet
from common.templates.default.care_assessment_v2 import CareAssessmentV2
from common.templates.default.delivery import Delivery
from common.templates.default.executive_summary import ExecutiveSummary
from common.templates.default.general import General
from common.templates.default.planning_committee import PlanningCommittee
from common.templates.types import Template
from common.types import TemplateMetadata

logger = logging.getLogger(__name__)


class TemplateNotFoundError(Exception):
    """Exception raised when a template is not found."""


# Explicit registration list
# . Add new system templates here
_TEMPLATES: tuple[type[Template], ...] = (
    General,
    PlanningCommittee,
    Cabinet,
    Delivery,
    CareAssessmentV2,
    ExecutiveSummary,
)


def _build_registry() -> dict[str, Template]:
    """Build the name -> Template mapping from the static registration list."""
    templates: dict[str, Template] = {}
    for template in _TEMPLATES:
        if template.name in templates:
            msg = (
                f"Failed loading '{template.name}'. A template with the same name has already been "
                f"registered. Please ensure template names are unique."
            )
            raise ValueError(msg)
        templates[template.name] = typing.cast("Template", template)
        logger.info("successfully registered template: %s", template.name)

    return templates


_REGISTRY: dict[str, Template] = _build_registry()


def get_templates() -> dict[str, Template]:
    """Get the mapping of template name to registered Template implementations."""
    return _REGISTRY


def get_template(name: str) -> Template:
    """Get a template instance by name."""
    try:
        return _REGISTRY[name]
    except KeyError as e:
        err_msg = f"Template '{name}' not found."
        raise TemplateNotFoundError(err_msg) from e


def get_template_metadata() -> list[TemplateMetadata]:
    """Get metadata for all registered templates."""
    return [
        TemplateMetadata(
            name=template.name,
            description=template.description,
            category=template.category,
            agenda_usage=template.agenda_usage,
        )
        for template in _REGISTRY.values()
    ]

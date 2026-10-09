"""Template library for minute generation.

Static registry - templates are listed here explicitly rather than discovered by
importlib inspection, so what exists is visible at a glance.
"""

from worker.templates.default.cabinet import Cabinet
from worker.templates.default.care_assessment_v2 import CareAssessmentV2
from worker.templates.default.delivery import Delivery
from worker.templates.default.executive_summary import ExecutiveSummary
from worker.templates.default.general import General
from worker.templates.default.planning_committee import PlanningCommittee
from worker.templates.types import Template

TEMPLATES: dict[str, type[Template]] = {
    template.name: template
    for template in [Cabinet, CareAssessmentV2, Delivery, ExecutiveSummary, General, PlanningCommittee]
}


class TemplateNotFoundError(Exception):
    """Exception raised when a template is not found."""


def get_template(name: str) -> type[Template]:
    try:
        return TEMPLATES[name]
    except KeyError as e:
        err_msg = f"Template '{name}' not found."
        raise TemplateNotFoundError(err_msg) from e

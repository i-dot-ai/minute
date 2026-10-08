"""Metadata-only template catalog for the backend templates endpoint.

The backend never imports the worker package, so template metadata (name, description,
category, agenda usage) is mirrored here as static data. The drift test asserts this
catalog matches the worker's template registry - update both when adding a template.
"""

from common.types import AgendaUsage, TemplateMetadata

TEMPLATE_CATALOG: list[TemplateMetadata] = [
    TemplateMetadata(
        name="Cabinet",
        description="Formal minutes following cabinet meeting structure",
        category="Formal Minutes",
        agenda_usage=AgendaUsage.OPTIONAL,
    ),
    TemplateMetadata(
        name="Care Assessment V2",
        description="Enhanced Social care assessment template based on Care Act Eligibility Criteria",
        category="Social Care",
        agenda_usage=AgendaUsage.NOT_USED,
    ),
    TemplateMetadata(
        name="Delivery",
        description="Formal minutes following the delivery style guide",
        category="Formal Minutes",
        agenda_usage=AgendaUsage.NOT_USED,
    ),
    TemplateMetadata(
        name="Short 'n' Sweet",
        description="Executive summary of the meeting + action items",
        category="Common",
        agenda_usage=AgendaUsage.NOT_USED,
    ),
    TemplateMetadata(
        name="General",
        description="Standard meeting summary with key points, decisions, and action items",
        category="Common",
        agenda_usage=AgendaUsage.OPTIONAL,
    ),
    TemplateMetadata(
        name="Planning Committee",
        description="Planning committee minutes template",
        category="Formal Minutes",
        agenda_usage=AgendaUsage.REQUIRED,
    ),
]

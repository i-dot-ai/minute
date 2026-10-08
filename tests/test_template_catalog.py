"""The backend serves template metadata from common/template_catalog.py, while generation
lives in worker/templates. This test is the guard against the two lists drifting apart."""

from common.template_catalog import TEMPLATE_CATALOG
from worker.templates import TEMPLATES


def test_catalog_covers_exactly_the_worker_templates():
    assert {meta.name for meta in TEMPLATE_CATALOG} == set(TEMPLATES)


def test_catalog_metadata_matches_worker_templates():
    catalog = {meta.name: meta for meta in TEMPLATE_CATALOG}
    for name, template in TEMPLATES.items():
        meta = catalog[name]
        assert template.description == meta.description, name
        assert template.category == meta.category, name
        assert template.agenda_usage == meta.agenda_usage, name

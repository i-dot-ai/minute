import pytest

from common.services.template_manager import TemplateManager
from tests.utils import get_test_client


@pytest.mark.asyncio(loop_scope="session")
@pytest.mark.parametrize("expected_status_code", [200])
async def test_get_templates_success(expected_status_code):
    async with get_test_client() as ac:
        response = await ac.get("/templates")
        assert response.status_code == expected_status_code
        assert len(response.json()) == len(TemplateManager.templates)

import pytest

from tests.utils import get_test_client


@pytest.mark.asyncio(loop_scope="session")
@pytest.mark.parametrize("expected_status_code", [200])
async def test_healthcheck_status_code(expected_status_code):
    async with get_test_client() as ac:
        response = await ac.get("/healthcheck")
        assert response.status_code == expected_status_code

"""Only the new route, real auth dependency and mocked Temporal; no database calls."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, Mock

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from backend.api.dependencies.get_current_user import get_current_user
from backend.api.dependencies.get_session import get_session
from backend.api.routes.status import status_router
from backend.utils import temporal_status
from common.services.exceptions import MissingAuthTokenError
from common.types import StatusResponse, StatusSummary


@pytest.fixture
def status_app():
    app = FastAPI()
    app.include_router(status_router)
    app.dependency_overrides[get_current_user] = lambda: object()
    return app


@pytest.mark.asyncio
async def test_route_defaults_normalizes_and_rejects_bad_horizons(status_app, monkeypatch):
    async def status(seconds):
        now = datetime.now(UTC)
        return StatusResponse(
            horizon_seconds=seconds,
            window_start=now,
            window_end=now,
            collected_at=now,
            partial=False,
            summary=StatusSummary(failure_rate=None, completed_per_minute=0),
            components={},
        )

    collect = AsyncMock(side_effect=status)
    monkeypatch.setattr(temporal_status, "get_status", collect)
    async with AsyncClient(transport=ASGITransport(app=status_app), base_url="http://test") as client:
        response = await client.get("/status")
        assert response.status_code == 200
        assert response.json()["horizon_seconds"] == 600
        for horizon, seconds in (("1m", 60), ("60m", 3_600), ("1h", 3_600), ("24h", 86_400)):
            assert (await client.get("/status", params={"horizon": horizon})).status_code == 200
            collect.assert_awaited_with(seconds)
        for horizon in ("0m", "-1m", "1.5h", "10s", "25h", "1441m", "10m OR 1=1"):
            assert (await client.get("/status", params={"horizon": horizon})).status_code == 422
    assert collect.await_count == 5


@pytest.mark.asyncio
async def test_unauthenticated_request_never_queries_temporal(status_app, monkeypatch):
    status_app.dependency_overrides.pop(get_current_user)
    status_app.dependency_overrides[get_session] = lambda: None
    monkeypatch.setattr(
        "backend.api.dependencies.get_current_user.get_user_info", Mock(side_effect=MissingAuthTokenError)
    )
    collect = AsyncMock()
    monkeypatch.setattr(temporal_status, "get_status", collect)
    async with AsyncClient(transport=ASGITransport(app=status_app), base_url="http://test") as client:
        assert (await client.get("/status")).status_code == 401
    collect.assert_not_awaited()


@pytest.mark.asyncio
@pytest.mark.parametrize("error", [TimeoutError(), RuntimeError("private Temporal address")])
async def test_temporal_failure_returns_generic_503(status_app, monkeypatch, error):
    monkeypatch.setattr(temporal_status, "get_status", AsyncMock(side_effect=error))
    async with AsyncClient(transport=ASGITransport(app=status_app), base_url="http://test") as client:
        response = await client.get("/status")
    assert response.status_code == 503
    assert response.json() == {"detail": "Processing status is temporarily unavailable"}

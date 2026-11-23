"""Tests for user display names and fixed departmental data retention.

Route tests need the docker-compose Postgres (`make run`); they run as the local-testing
user (name.surname@domain.gov.uk), or synthetic users deleted afterwards.
"""

from types import SimpleNamespace
from uuid import uuid4

import pytest
from sqlmodel import delete, select, update
from sqlmodel.ext.asyncio.session import AsyncSession

from common.database.postgres_database import async_engine
from common.database.postgres_models import User
from common.services.user_details import display_name_from_email
from tests.utils import get_test_client


@pytest.mark.parametrize(
    ("email", "expected"),
    [
        ("jane.smith@example.gov.uk", "Jane Smith"),
        ("jane.o.smith@example.com", "Jane O Smith"),
        ("jane.smith-jones@example.com", "Jane Smith-Jones"),
        ("j.o.smith-jones@example.com", "J O Smith-Jones"),
        ("jane.smith-jones2@example.com", "Jane Smith-Jones"),
        ("jane.smith3@example.com", "Jane Smith"),
        ("j.o.smith@example.com", "J O Smith"),
        ("jsmith@example.com", "Jsmith"),
        ("JANE.Smith@Example.COM", "Jane Smith"),
        ("j@example.com", "J"),
        (".jane.@example.com", "Jane"),
        ("jane.smith.2@example.com", "Jane Smith"),
        ("jane.2@example.com", "Jane"),
        # Nothing usable before the '+' means the raw local part is the least-bad fallback.
        ("+tag@example.com", "+Tag"),
    ],
)
def test_display_name_from_email(email, expected):
    assert display_name_from_email(email) == expected


@pytest.mark.asyncio(loop_scope="session")
async def test_display_name_defaults_to_email_derived():
    async with get_test_client() as ac:
        me = (await ac.get("/users/me")).json()
        assert me["email"] == "name.surname@domain.gov.uk"  # the local-testing identity
        assert me["display_name"] == display_name_from_email(me["email"]) == "Name Surname"


@pytest.mark.asyncio(loop_scope="session")
async def test_display_name_patch_set_clear_and_validation():
    async with get_test_client() as ac:
        try:
            set_response = await ac.patch("/users/display-name", json={"display_name": "  Jane Smith  "})
            assert set_response.status_code == 200
            assert set_response.json()["display_name"] == "Jane Smith"  # stored trimmed

            me = (await ac.get("/users/me")).json()
            assert me["display_name"] == "Jane Smith"

            # Omitting the field is a no-op, not a clear.
            untouched = await ac.patch("/users/display-name", json={})
            assert untouched.status_code == 200
            assert untouched.json()["display_name"] == "Jane Smith"

            cleared = await ac.patch("/users/display-name", json={"display_name": None})
            assert cleared.status_code == 200
            assert cleared.json()["display_name"] == display_name_from_email("name.surname@domain.gov.uk")

            blank = await ac.patch("/users/display-name", json={"display_name": "   "})
            assert blank.status_code == 400

            # An exact empty string skips the model's length check entirely and
            # must hit the same route-level blank rejection.
            empty = await ac.patch("/users/display-name", json={"display_name": ""})
            assert empty.status_code == 400

            too_long = await ac.patch("/users/display-name", json={"display_name": "x" * 101})
            assert too_long.status_code == 422
        finally:
            await ac.patch("/users/display-name", json={"display_name": None})


@pytest.mark.asyncio(loop_scope="session")
@pytest.mark.parametrize(
    ("domain", "original_retention", "fixed"),
    [
        ("businessandtrade.gov.uk", None, True),
        ("BUSINESSANDTRADE.GOV.UK", 90, True),
        ("businessandtrade.gov.uk", 7, True),
        ("dsit.gov.uk", None, False),
        ("sub.businessandtrade.gov.uk", 90, False),
        ("notbusinessandtrade.gov.uk", 7, False),
        ("businessandtrade.gov.uk.example.com", None, False),
    ],
)
async def test_fixed_data_retention(monkeypatch, domain, original_retention, fixed):
    email = f"retention-test-{uuid4().hex}@{domain}"
    monkeypatch.setattr(
        "backend.api.dependencies.get_current_user.get_user_info",
        lambda _: SimpleNamespace(email=email, is_authorised=True),
    )
    try:
        async with get_test_client() as ac:
            created = await ac.get("/users/me")
            assert created.status_code == 200
            assert created.json()["data_retention_days"] == 30

            async with AsyncSession(async_engine) as session:
                await session.exec(
                    update(User).where(User.email == email.lower()).values(data_retention_days=original_retention)
                )
                await session.commit()

            existing = await ac.get("/users/me")
            assert existing.status_code == 200
            assert existing.json()["data_retention_days"] == (30 if fixed else original_retention)

            for days in (7, None):
                changed = await ac.patch("/users/data-retention", json={"data_retention_days": days})
                assert changed.status_code == (403 if fixed else 200)
                if not fixed:
                    assert changed.json()["data_retention_days"] == days

            async with AsyncSession(async_engine) as session:
                stored = (await session.exec(select(User).where(User.email == email.lower()))).one()
                assert stored.data_retention_days == (30 if fixed else None)
    finally:
        async with AsyncSession(async_engine) as session:
            await session.exec(delete(User).where(User.email == email.lower()))
            await session.commit()

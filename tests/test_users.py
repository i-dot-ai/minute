"""Tests for user display names: the email-derived fallback and PATCH /users/display-name.

Route tests need the docker-compose Postgres (`make run`); they run as the local-testing
user (name.surname@domain.gov.uk) and restore its display name afterwards.
"""

import pytest

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

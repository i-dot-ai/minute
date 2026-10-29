import uuid

import pytest

from common.services.template_manager import TemplateManager
from tests.utils import get_test_client


@pytest.mark.asyncio(loop_scope="session")
async def test_get_templates_success():
    async with get_test_client() as ac:
        response = await ac.get("/templates")
        assert response.status_code == 200
        assert len(response.json()) == len(TemplateManager.templates)


async def _create_user_template(ac, name: str) -> str:
    response = await ac.post(
        "/user-templates",
        json={
            "name": name,
            "content": "<p>content</p>",
            "description": "desc",
            "type": "document",
            "questions": [],
        },
    )
    assert response.status_code == 200
    templates = (await ac.get("/user-templates")).json()
    return next(template["id"] for template in templates if template["name"] == name)


async def _clear_default(ac) -> None:
    await ac.patch("/users/default-template", json={})


@pytest.mark.asyncio(loop_scope="session")
async def test_set_default_template():
    """Setting, overwriting (either direction) and validating the user's default template."""
    async with get_test_client() as ac:
        system_name = (await ac.get("/templates")).json()[0]["name"]
        template_id = await _create_user_template(ac, "Default me")
        try:
            # A user template can be the default.
            response = await ac.patch("/users/default-template", json={"template_id": template_id})
            assert response.status_code == 200
            assert response.json()["default_template_id"] == template_id
            assert response.json()["default_template_name"] is None

            templates = (await ac.get("/user-templates")).json()
            assert all(t["is_default"] == (t["id"] == template_id) for t in templates)

            me = (await ac.get("/users/me")).json()
            assert me["default_template_id"] == template_id

            # A system template can be the default, overwriting the user one.
            response = await ac.patch("/users/default-template", json={"template_name": system_name})
            assert response.status_code == 200
            assert response.json()["default_template_name"] == system_name
            assert response.json()["default_template_id"] is None

            templates = (await ac.get("/templates")).json()
            assert all(t["is_default"] == (t["name"] == system_name) for t in templates)

            # ...and the user template overwrites it back.
            await ac.patch("/users/default-template", json={"template_name": system_name})
            await ac.patch("/users/default-template", json={"template_id": template_id})
            me = (await ac.get("/users/me")).json()
            assert me["default_template_id"] == template_id
            assert me["default_template_name"] is None

            # Supplying both, or an unknown name/id, is rejected.
            both = await ac.patch(
                "/users/default-template",
                json={"template_id": template_id, "template_name": system_name},
            )
            assert both.status_code == 400

            bad_name = await ac.patch("/users/default-template", json={"template_name": "Not a real template"})
            assert bad_name.status_code == 404

            bad_id = await ac.patch("/users/default-template", json={"template_id": str(uuid.uuid4())})
            assert bad_id.status_code == 404
        finally:
            await _clear_default(ac)
            await ac.delete(f"/user-templates/{template_id}")


@pytest.mark.asyncio(loop_scope="session")
async def test_delete_default_template_clears_pointer():
    async with get_test_client() as ac:
        template_id = await _create_user_template(ac, "Delete me")
        await ac.patch("/users/default-template", json={"template_id": template_id})

        await ac.delete(f"/user-templates/{template_id}")

        me = (await ac.get("/users/me")).json()
        assert me["default_template_id"] is None


_XSS_CONTENT = '<p>Legit <strong>bold</strong></p><img src=x onerror="alert(1)"><script>alert(1)</script>'
_SANITISED_CONTENT = "<p>Legit <strong>bold</strong></p>"


@pytest.mark.asyncio(loop_scope="session")
async def test_user_template_content_is_sanitised():
    async with get_test_client() as ac:
        response = await ac.post(
            "/user-templates",
            json={
                "name": "XSS create",
                "content": _XSS_CONTENT,
                "description": "desc",
                "type": "document",
                "questions": [],
            },
        )
        assert response.status_code == 200
        templates = (await ac.get("/user-templates")).json()
        template_id = next(t["id"] for t in templates if t["name"] == "XSS create")
        try:
            assert next(t for t in templates if t["id"] == template_id)["content"] == _SANITISED_CONTENT

            # Editing goes through the same sanitiser.
            response = await ac.patch(f"/user-templates/{template_id}", json={"content": _XSS_CONTENT})
            assert response.status_code == 200

            template = (await ac.get(f"/user-templates/{template_id}")).json()
            assert template["content"] == _SANITISED_CONTENT
        finally:
            await ac.delete(f"/user-templates/{template_id}")

"""The public development stack must not depend on private infrastructure files."""

from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]


def test_local_compose_build_inputs_are_self_contained():
    compose = yaml.safe_load((ROOT / "docker-compose.yaml").read_text())
    for service in compose["services"].values():
        if build := service.get("build"):
            assert build["context"] == "."
            assert (ROOT / build["dockerfile"]).is_file()
    assert (ROOT / "temporal/version.env").is_file()
    assert (ROOT / "temporal-admin/entrypoint.sh").is_file()
    assert "terraform" not in (ROOT / "Makefile").read_text()
    assert not list((ROOT / "terraform").glob("*.tf"))
    assert not list((ROOT / "terraform-temporal").glob("*.tf"))
    for name in ("backend", "worker"):
        dependency = compose["services"][name]["depends_on"]["temporal-namespace"]
        assert dependency["condition"] == "service_completed_successfully"


def test_public_workflows_do_not_publish_or_deploy():
    paths = list((ROOT / ".github/workflows").glob("*.yml"))
    assert {path.name for path in paths} == {"checks.yml", "pre-commit.yml", "e2e-mocked.yml"}
    for path in paths:
        text = path.read_text()
        assert "id-token: write" not in text
        assert "secrets." not in text
        assert "i-dot-ai-core-github-actions" not in text

"""Release routing must never apply the other component's Terraform root or publish its images."""

# ruff: noqa: S603, S607 # Commands use fixed test arguments and stubbed git/AWS/Terraform binaries.

import os
import subprocess
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def commands(tmp_path):
    log = tmp_path / "commands"
    for command in ("git", "terraform", "aws", "jq", "python3"):
        script = tmp_path / command
        script.write_text(
            '#!/bin/sh\nprintf "%s %s\\n" "$(basename "$0")" "$*" >> "$COMMAND_LOG"\n'
            'case "$1" in rev-parse) echo test-commit ;; batch-get-image) echo manifest ;; esac\n'
            'if [ "$(basename "$0")" = jq ]; then exit "${JQ_STATUS:-0}"; fi\n'
            'if [ "$(basename "$0")" = python3 ]; then exit "${ADMIN_STATUS:-0}"; fi\n'
        )
        script.chmod(0o755)
    return {**os.environ, "PATH": f"{tmp_path}:{os.environ['PATH']}", "COMMAND_LOG": str(log)}, log


@pytest.mark.parametrize(
    ("target", "prefix"), [("release", "release-dev-"), ("release-temporal-server", "release-temporal-server-dev-")]
)
def test_release_tags_select_only_one_component(commands, target, prefix):
    env, log = commands
    subprocess.run(["make", target, "env=dev"], cwd=ROOT, env=env, check=True, capture_output=True)
    pushes = [line for line in log.read_text().splitlines() if line.startswith("git push")]
    assert len(pushes) == 1
    assert pushes[0].startswith(f"git push origin {prefix}")


@pytest.mark.parametrize(
    ("environment", "component"), [("prod", "app"), ("prod", "temporal-server"), ("invalid", "app"), ("dev", "unknown")]
)
def test_invalid_releases_do_not_push(commands, environment, component):
    env, log = commands
    result = subprocess.run(
        ["bash", "release.sh", environment, component], cwd=ROOT, env=env, capture_output=True, check=False
    )
    assert result.returncode != 0
    assert not log.exists() or "git push" not in log.read_text()


@pytest.mark.parametrize("folder", ["terraform", "terraform-temporal"])
def test_make_applies_and_tags_only_selected_component(commands, folder):
    env, log = commands
    repos = (
        "minute-temporal,minute-temporal-admin"
        if folder == "terraform-temporal"
        else "minute-backend,minute-frontend,minute-worker"
    )
    args = ["make", f"INFRASTRUCTURE_FOLDER={folder}", "env=dev", "IMAGE_TAG=test-commit", "ECR_REPO=wrong-repository"]
    subprocess.run([*args, "tf_auto_apply"], cwd=ROOT, env=env, check=True, capture_output=True)
    subprocess.run([*args, "docker_update_tag", "tag=dev"], cwd=ROOT, env=env, check=True, capture_output=True)
    lines = log.read_text().splitlines()
    terraform = [line for line in lines if line.startswith("terraform ")]
    assert terraform
    assert all(line.startswith(f"terraform -chdir={folder} ") for line in terraform)
    assert any(" apply " in line for line in terraform)
    aws = [line for line in lines if line.startswith("aws ")]
    assert aws
    assert all(any(f"--repository-name {repo} " in line for repo in repos.split(",")) for line in aws)
    if folder == "terraform-temporal":
        schema = lines.index("python3 temporal-admin/run_task.py schema")
        namespace = lines.index("python3 temporal-admin/run_task.py namespace")
        applies = [i for i, line in enumerate(lines) if line.startswith("terraform ") and " apply " in line]
        assert applies[0] < schema < applies[1] < namespace
    else:
        assert not any(line.startswith("python3 temporal-admin/") for line in lines)


def test_missing_images_stop_before_terraform_apply(commands):
    env, log = commands
    result = subprocess.run(
        ["make", "tf_auto_apply", "env=dev", "INFRASTRUCTURE_FOLDER=terraform-temporal", "IMAGE_TAG=test-commit"],
        cwd=ROOT,
        env={**env, "JQ_STATUS": "1"},
        capture_output=True,
        check=False,
    )
    assert result.returncode != 0
    assert "terraform " not in log.read_text()


def test_failed_migration_leaves_server_unchanged(commands):
    env, log = commands
    result = subprocess.run(
        ["make", "tf_auto_apply", "env=dev", "INFRASTRUCTURE_FOLDER=terraform-temporal", "IMAGE_TAG=test-commit"],
        cwd=ROOT,
        env={**env, "ADMIN_STATUS": "1"},
        check=False,
        capture_output=True,
    )
    assert result.returncode != 0
    applies = [line for line in log.read_text().splitlines() if line.startswith("terraform ") and " apply " in line]
    assert len(applies) == 1
    assert "-target=aws_ecs_task_definition.temporal_admin" in applies[0]
    assert "namespace" not in log.read_text()


def test_image_tagging_publishes_only_selected_repository(commands):
    env, log = commands
    subprocess.run(
        ["make", "docker_update_tag", "tag=dev", "INFRASTRUCTURE_FOLDER=terraform-temporal", "IMAGE_TAG=test-commit"],
        cwd=ROOT,
        env={**env, "JQ_STATUS": "1"},
        capture_output=True,
        check=True,
    )
    published = [line for line in log.read_text().splitlines() if line.startswith("aws ecr put-image")]
    assert len(published) == 2
    assert "--repository-name minute-temporal --image-tag dev" in published[0]
    assert "--repository-name minute-temporal-admin --image-tag dev" in published[1]


@pytest.mark.parametrize(
    ("event", "ref", "component", "environment", "expected_folder"),
    [
        ("push", "release-dev-feature-test", "", "", "terraform"),
        ("push", "release-preprod-feature-test", "", "", "terraform"),
        ("push", "release-temporal-server-dev-feature-test", "", "", "terraform-temporal"),
        ("push", "release-temporal-server-preprod-feature-test", "", "", "terraform-temporal"),
        ("workflow_dispatch", "main", "app", "prod", "terraform"),
        ("workflow_dispatch", "main", "temporal-server", "prod", "terraform-temporal"),
        ("workflow_dispatch", "feature", "temporal-server", "prod", None),
    ],
)
def test_github_release_routing(commands, tmp_path, event, ref, component, environment, expected_folder):
    env, _ = commands
    output = tmp_path / "outputs"
    workflow = yaml.safe_load((ROOT / ".github/workflows/release.yml").read_text())
    script = next(step["run"] for step in workflow["jobs"]["set-vars"]["steps"] if step.get("id") == "env-var")
    result = subprocess.run(
        ["bash", "-eu", "-c", script],
        cwd=ROOT,
        capture_output=True,
        check=False,
        env={
            **env,
            "GITHUB_OUTPUT": str(output),
            "RELEASE_REF": ref,
            "RELEASE_EVENT": event,
            "RELEASE_COMPONENT": component,
            "RELEASE_ENVIRONMENT": environment,
            "SERVER_UPGRADE_REVIEWED": "true",
        },
    )
    if expected_folder is None:
        assert result.returncode != 0
        assert not output.exists()
    else:
        assert result.returncode == 0
        assert f"infrastructure-folder={expected_folder}" in output.read_text()


def test_workflow_and_state_ownership_are_separate():
    workflow = yaml.safe_load((ROOT / ".github/workflows/release.yml").read_text())
    build = yaml.safe_load((ROOT / ".github/workflows/build.yml").read_text())
    assert "temporal" not in build["jobs"]
    assert workflow["jobs"]["build-temporal"]["with"]["service"] == "temporal"
    assert workflow["jobs"]["build-temporal-admin"]["with"]["service"] == "temporal-admin"
    assert "build-temporal" in workflow["jobs"]["apply-infra"]["needs"]
    assert "build-temporal-admin" in workflow["jobs"]["apply-infra"]["needs"]
    assert "infrastructure-folder" in workflow["jobs"]["apply-infra"]["with"]["INFRASTRUCTURE_FOLDER"]
    application = "\n".join(path.read_text() for path in (ROOT / "terraform").glob("*.tf"))
    assert 'module "temporal"' not in application
    assert 'module "temporal_db"' not in application
    server = (ROOT / "terraform-temporal/main.tf").read_text()
    assert 'module "temporal"' in server
    assert 'module "temporal_db"' in server
    assert 'module "backend"' not in server
    assert 'module "worker"' not in server
    assert 'key = "minute-temporal/terraform.tfstate"' in (ROOT / "terraform-temporal/provider.tf").read_text()
    assert "removed {" not in application
    assert 'key = "minute/terraform.tfstate"' in (ROOT / "terraform/provider.tf").read_text()


def test_production_server_release_requires_upgrade_acknowledgement(commands, tmp_path):
    env, _ = commands
    output = tmp_path / "outputs"
    workflow = yaml.safe_load((ROOT / ".github/workflows/release.yml").read_text())
    script = next(step["run"] for step in workflow["jobs"]["set-vars"]["steps"] if step.get("id") == "env-var")
    result = subprocess.run(
        ["bash", "-eu", "-c", script],
        cwd=ROOT,
        capture_output=True,
        check=False,
        env={
            **env,
            "GITHUB_OUTPUT": str(output),
            "RELEASE_REF": "main",
            "RELEASE_EVENT": "workflow_dispatch",
            "RELEASE_COMPONENT": "temporal-server",
            "RELEASE_ENVIRONMENT": "prod",
            "SERVER_UPGRADE_REVIEWED": "false",
        },
    )
    assert result.returncode != 0
    assert not output.exists()

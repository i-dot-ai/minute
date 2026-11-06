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
    for command in ("git", "terraform", "aws", "jq", "python3", "docker"):
        script = tmp_path / command
        script.write_text(
            '#!/bin/sh\nprintf "%s %s\\n" "$(basename "$0")" "$*" >> "$COMMAND_LOG"\n'
            'case "$1" in rev-parse) echo test-commit ;; batch-get-image) echo manifest ;; esac\n'
            'if [ "$(basename "$0")" = jq ]; then exit "${JQ_STATUS:-0}"; fi\n'
            'if [ "$(basename "$0")" = python3 ]; then exit "${ADMIN_STATUS:-0}"; fi\n'
        )
        script.chmod(0o755)
    return {**os.environ, "PATH": f"{tmp_path}:{os.environ['PATH']}", "COMMAND_LOG": str(log)}, log


@pytest.mark.parametrize("folder", ["terraform", "terraform-temporal"])
def test_make_applies_and_tags_only_selected_component(commands, folder):
    env, log = commands
    if folder == "terraform":
        env = {**env, "ADMIN_STATUS": "1"}
    repos = "minute-temporal" if folder == "terraform-temporal" else "minute-backend,minute-frontend,minute-worker"
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
    assert "--repository-name minute-temporal --image-tag dev-admin" in published[1]
    fetched = [line for line in log.read_text().splitlines() if line.startswith("aws ecr batch-get-image")]
    assert "imageTag=test-commit " in fetched[0]
    assert "imageTag=test-commit-admin " in fetched[1]


@pytest.mark.parametrize("service", ["temporal", "temporal-admin"])
def test_server_and_admin_images_share_repository_not_tags(commands, service):
    env, log = commands
    args = [
        "make",
        f"service={service}",
        "APP_NAME=minute",
        "AWS_ACCOUNT_ID=123",
        "AWS_REGION=eu-west-2",
        "IMAGE_TAG=test-commit",
    ]
    subprocess.run([*args, "docker_build_local", "docker_push"], cwd=ROOT, env=env, check=True, capture_output=True)
    tag = "test-commit-admin" if service == "temporal-admin" else "test-commit"
    image = f"123.dkr.ecr.eu-west-2.amazonaws.com/minute-temporal:{tag}"
    lines = log.read_text().splitlines()
    assert any(f"-t {image} " in line and f"-f {service}/Dockerfile" in line for line in lines)
    assert f"docker push {image}" in lines
    assert "minute-temporal-admin:" not in log.read_text()


@pytest.mark.parametrize("service", ["backend", "worker", "temporal", "temporal-admin"])
@pytest.mark.parametrize("cache", [None, "/mnt/efs"])
def test_docker_build_isolates_service_caches_and_keeps_intermediate_layers(commands, service, cache):
    env, log = commands
    args = ["make", "docker_build", f"service={service}", "APP_NAME=minute", "IMAGE_TAG=test-commit"]
    if cache:
        args.append(f"cache={cache}")
    subprocess.run(args, cwd=ROOT, env=env, check=True, capture_output=True)
    path = f"{cache or './.build-cache'}/minute/{service}"
    command = next(line for line in log.read_text().splitlines() if line.startswith("docker buildx build"))
    assert f"--cache-to type=local,dest={path},mode=max " in command
    assert f"--cache-from type=local,src={path} " in command


def test_frontend_release_pushes_without_loading_and_keeps_its_own_cache():
    workflow = yaml.safe_load((ROOT / ".github/workflows/build-fe.yml").read_text())
    build = next(step["with"] for step in workflow["jobs"]["build-image"]["steps"] if step.get("name") == "Build")
    assert build["push"] is True
    assert not build.get("load", False)
    assert build["cache-to"] == "type=local,dest=${{ env.EFS_MOUNT_PATH }}/minute/frontend,mode=max"
    assert build["cache-from"] == "type=local,src=${{ env.EFS_MOUNT_PATH }}/minute/frontend"


@pytest.mark.parametrize("service", ["backend", "worker"])
def test_python_images_keep_non_root_runtime_without_recursively_chowning_dependencies(service):
    dockerfile = (ROOT / service / "Dockerfile").read_text()
    assert "USER appuser" in dockerfile
    assert "useradd --create-home appuser" in dockerfile
    assert "mkdir -p /app/config && chown appuser:appuser /app /app/config" in dockerfile
    assert "chown -R" not in dockerfile
    assert dockerfile.index("useradd") < dockerfile.index("uv sync")


def test_missing_admin_image_stops_before_migrations(commands):
    env, log = commands
    jq = Path(env["PATH"].split(":")[0]) / "jq"
    jq.write_text(
        '#!/bin/sh\ncat >/dev/null\nif grep -q "imageTag=test-commit-admin" "$COMMAND_LOG"; then exit 1; fi\n'
    )
    result = subprocess.run(
        ["make", "tf_auto_apply", "env=dev", "INFRASTRUCTURE_FOLDER=terraform-temporal", "IMAGE_TAG=test-commit"],
        cwd=ROOT,
        env=env,
        capture_output=True,
        check=False,
    )
    assert result.returncode != 0
    assert "imageTag=test-commit-admin" in log.read_text()
    assert " apply " not in log.read_text()
    assert "python3 temporal-admin/" not in log.read_text()


@pytest.mark.parametrize(
    ("event", "ref", "component", "environment", "expected_folder"),
    [
        ("push", "release-dev-feature-test", "", "", "terraform"),
        ("push", "release-preprod-feature-test", "", "", "terraform"),
        ("push", "release-temporal-server-dev-feature-test", "", "", "terraform-temporal"),
        ("push", "release-temporal-server-preprod-feature-test", "", "", "terraform-temporal"),
        ("workflow_dispatch", "main", "app", "prod", "terraform"),
        ("workflow_dispatch", "main", "temporal-server", "prod", "terraform-temporal"),
        ("workflow_dispatch", "main", "temporal-admin", "dev", None),
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
    assert workflow["jobs"]["build-app"]["uses"] == "./.github/workflows/build.yml"
    assert "build-app" in workflow["jobs"]["apply-infra"]["needs"]
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


def test_image_publication_is_release_only_and_uses_the_resolved_commit():
    release = yaml.safe_load((ROOT / ".github/workflows/release.yml").read_text())
    app_build = yaml.safe_load((ROOT / ".github/workflows/build.yml").read_text())
    # PyYAML's YAML 1.1 loader reads the unquoted GitHub Actions `on` key as True.
    assert set(app_build[True]) == {"workflow_call"}
    for name in ("build-app", "build-temporal", "build-temporal-admin"):
        assert release["jobs"][name]["with"]["image_tag"] == "${{ needs.set-vars.outputs.image-tag }}"
        assert name in release["jobs"]["apply-infra"]["needs"]
        assert name in release["jobs"]["stop-runner"]["needs"]
    for job in app_build["jobs"].values():
        assert job["with"]["image_tag"] == "${{ inputs.image_tag }}"
    for filename in ("build-one.yml", "build-fe.yml"):
        workflow = yaml.safe_load((ROOT / ".github/workflows" / filename).read_text())
        assert set(workflow[True]) == {"workflow_call"}
        assert workflow["jobs"]["start-runner"]["if"] == "needs.set-vars.outputs.image-exists == 'false'"
        assert workflow["concurrency"]["cancel-in-progress"] is False
        assert any(
            step.get("run") == "bash .github/scripts/image-exists.sh" for step in workflow["jobs"]["set-vars"]["steps"]
        )
    backend = yaml.safe_load((ROOT / ".github/workflows/build-one.yml").read_text())
    frontend = yaml.safe_load((ROOT / ".github/workflows/build-fe.yml").read_text())
    assert backend["jobs"]["build-image"]["with"]["COMMIT_HASH"] == "${{ inputs.image_tag }}"
    assert frontend["jobs"]["build-image"]["steps"][0]["with"]["ref"] == "${{ inputs.image_tag }}"
    build = next(step for step in frontend["jobs"]["build-image"]["steps"] if step.get("name") == "Build")
    assert build["with"]["tags"].endswith(":${{ inputs.image_tag }}")


def test_deployment_requires_successful_component_builds():
    workflow = yaml.safe_load((ROOT / ".github/workflows/release.yml").read_text())
    condition = workflow["jobs"]["apply-infra"]["if"]
    assert "needs.set-vars.outputs.component == 'app' && needs.build-app.result == 'success'" in condition
    assert (
        "needs.set-vars.outputs.component == 'temporal-server' && needs.build-temporal.result == 'success' "
        "&& needs.build-temporal-admin.result == 'success'"
    ) in condition
    assert "'skipped'" not in condition


@pytest.mark.parametrize(
    ("status", "response", "expected"),
    [
        (0, "sha256:" + "a" * 64, "true"),
        (254, "An error occurred (ImageNotFoundException) when calling DescribeImages", "false"),
        (254, "An error occurred (AccessDeniedException) when calling DescribeImages", None),
        (254, "An error occurred (RepositoryNotFoundException) when calling DescribeImages", None),
        (255, "Could not connect to the endpoint URL", None),
        (0, "None", None),
        (0, "unexpected-response", None),
    ],
)
def test_existing_image_lookup_fails_closed(commands, tmp_path, status, response, expected):
    env, log = commands
    aws = tmp_path / "aws"
    aws.write_text(
        '#!/bin/sh\nprintf "aws %s\\n" "$*" >> "$COMMAND_LOG"\n' 'printf "%s\\n" "$ECR_RESPONSE"\nexit "$ECR_STATUS"\n'
    )
    output = tmp_path / "outputs"
    result = subprocess.run(
        ["bash", ".github/scripts/image-exists.sh"],
        cwd=ROOT,
        env={
            **env,
            "ECR_REPOSITORY": "minute-temporal",
            "IMAGE_TAG": "test-commit-admin",
            "ECR_RESPONSE": response,
            "ECR_STATUS": str(status),
            "GITHUB_OUTPUT": str(output),
        },
        capture_output=True,
        check=False,
    )
    if expected is None:
        assert result.returncode != 0
        assert not output.exists()
    else:
        assert result.returncode == 0
        assert output.read_text() == f"exists={expected}\n"
    assert "--repository-name minute-temporal --image-ids imageTag=test-commit-admin" in log.read_text()
    assert "docker" not in log.read_text()


def test_commit_checks_build_locally_without_publishing():
    workflow = yaml.safe_load((ROOT / ".github/workflows/checks.yml").read_text())
    assert "pull_request" in workflow[True]
    assert workflow[True]["push"]["branches"] == ["main"]
    assert workflow["permissions"] == {"contents": "read"}
    build = workflow["jobs"]["local_build"]
    assert build["runs-on"] == "ubuntu-latest"
    script = next(
        step["run"]
        for step in build["steps"]
        if step.get("name") == "Validate and build local services without publishing"
    )
    assert "source temporal/version.env" in script
    assert "docker compose config --quiet" in script
    assert "docker compose build" in script
    permissions = build["steps"][-1]["run"]
    assert "for service in backend worker" in permissions
    assert "--no-deps -T --entrypoint python" in permissions
    assert "assert os.getuid() != 0" in permissions
    assert 'TemporaryDirectory(dir="/app/config")' in permissions
    text = (ROOT / ".github/workflows/checks.yml").read_text()
    for forbidden in ("docker push", "push: true", "secrets.", "id-token: write", "apt-get"):
        assert forbidden not in text
    assert "environment" not in workflow["jobs"]["run_tests"]


def test_slack_runs_despite_failed_or_skipped_deployment_dependencies():
    workflow = yaml.safe_load((ROOT / ".github/workflows/release.yml").read_text())
    notification = workflow["jobs"]["notify-slack"]
    assert notification["if"] == "${{ always() && needs.set-vars.result == 'success' }}"
    assert "apply-infra" in notification["needs"]
    assert notification["with"]["RUNNER_LABEL"] == "ubuntu-latest"
    assert "needs.apply-infra.result == 'success'" in notification["with"]["WORKFLOW_PASSED"]
    admin = (ROOT / "terraform-temporal/admin.tf").read_text()
    assert "amazonaws.com/minute-temporal:${var.image_tag}-admin" in admin
    assert "amazonaws.com/minute-temporal-admin:" not in admin


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

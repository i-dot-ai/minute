"""Admin releases fail closed, and bootstrap never overwrites an existing database schema."""

# ruff: noqa: S603, S607 # Tests execute fixed scripts with fake local commands, never AWS.

import importlib.util
import json
import os
import subprocess
from pathlib import Path
from unittest.mock import Mock

import pytest

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def task_runner():
    spec = importlib.util.spec_from_file_location("temporal_admin_task", ROOT / "temporal-admin/run_task.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def admin_commands(tmp_path):
    log = tmp_path / "commands"
    scripts = {
        "psql": """case "$*" in
  *pg_tables*) echo "${TABLE_COUNT:-0}" ;;
  *"SELECT rolsuper"*) echo "${RUNTIME_SUPERUSER:-f}" ;;
  *) sql=$(cat); case "$sql" in
    *pg_database*) echo "${DATABASE_EXISTS:-t}" ;;
    *to_regclass*) echo "${SCHEMA_EXISTS:-t}" ;;
  esac ;;
esac
printf '%s\\n' "${sql:-}" >> "$COMMAND_LOG"
case "${sql:-}" in *"PASSWORD :'password' NOSUPERUSER"*) exit 3 ;; esac
exit "${PSQL_STATUS:-0}"
""",
        "temporal-sql-tool": 'exit "${MIGRATION_STATUS:-0}"\n',
        "temporal": """case "$*" in
  *"namespace list"*) printf '%s' "${NAMESPACES:-[]}"; exit "${NAMESPACE_STATUS:-0}" ;;
esac
""",
    }
    for name, body in scripts.items():
        script = tmp_path / name
        script.write_text('#!/bin/sh\nprintf "%s %s\\n" "$(basename "$0")" "$*" >> "$COMMAND_LOG"\n' + body)
        script.chmod(0o755)
    return {
        **os.environ,
        "PATH": f"{tmp_path}:{os.environ['PATH']}",
        "COMMAND_LOG": str(log),
        "POSTGRES_SEEDS": "test-db",
        "POSTGRES_USER": "admin",
        "POSTGRES_PWD": "test-password",
        "TEMPORAL_ADDRESS": "test-server:7233",
    }, log


@pytest.mark.parametrize(("database", "schema", "setup"), [("f", "f", True), ("t", "f", True), ("t", "t", False)])
def test_schema_bootstrap_or_upgrade(admin_commands, database, schema, setup):
    env, log = admin_commands
    subprocess.run(
        ["sh", "temporal-admin/entrypoint.sh"],
        cwd=ROOT,
        env={**env, "DATABASE_EXISTS": database, "SCHEMA_EXISTS": schema},
        check=True,
        capture_output=True,
    )
    lines = log.read_text().splitlines()
    assert sum(" create" in line for line in lines) == (2 if database == "f" else 0)
    assert sum("setup-schema" in line for line in lines) == (2 if setup else 0)
    assert sum("update-schema" in line for line in lines) == 2


@pytest.mark.parametrize(
    "failure", [{"PSQL_STATUS": "1"}, {"MIGRATION_STATUS": "1"}, {"SCHEMA_EXISTS": "f", "TABLE_COUNT": "3"}]
)
def test_schema_failure_is_not_swallowed(admin_commands, failure):
    env, log = admin_commands
    result = subprocess.run(
        ["sh", "temporal-admin/entrypoint.sh"], cwd=ROOT, env={**env, **failure}, check=False, capture_output=True
    )
    assert result.returncode != 0
    assert "namespace" not in log.read_text()


@pytest.mark.parametrize("superuser", ["f", "t"])
def test_runtime_role_setup_does_not_require_superuser_privileges(admin_commands, superuser):
    env, log = admin_commands
    result = subprocess.run(
        ["sh", "temporal-admin/entrypoint.sh"],
        cwd=ROOT,
        env={**env, "TEMPORAL_RUNTIME_PASSWORD": "runtime-password", "RUNTIME_SUPERUSER": superuser},
        check=False,
        capture_output=True,
    )
    assert (result.returncode == 0) is (superuser == "f")
    sql = log.read_text()
    assert "PASSWORD :'password' NOCREATEDB NOCREATEROLE" in sql
    assert "PASSWORD :'password' NOSUPERUSER" not in sql
    assert ("GRANT USAGE ON SCHEMA" in sql) is (superuser == "f")


@pytest.mark.parametrize(
    ("namespaces", "status", "creates"),
    [
        ("[]", "0", True),
        ('[{"namespaceInfo":{"name":"default"}}]', "0", False),
        ("[]", "1", False),
        ("invalid-json", "0", False),
    ],
)
def test_namespace_creation_only_after_successful_lookup(admin_commands, namespaces, status, creates):
    env, log = admin_commands
    result = subprocess.run(
        ["sh", "temporal-admin/entrypoint.sh", "namespace"],
        cwd=ROOT,
        env={**env, "NAMESPACES": namespaces, "NAMESPACE_STATUS": status},
        check=False,
        capture_output=True,
    )
    assert (result.returncode == 0) is (status == "0" and namespaces != "invalid-json")
    assert ("namespace create" in log.read_text()) is creates
    assert "temporal-sql-tool" not in log.read_text()


@pytest.mark.parametrize("exit_code", [0, 1, None])
def test_ecs_task_requires_successful_exit(monkeypatch, exit_code, task_runner):
    module = task_runner
    config = {
        "region": "eu-west-2",
        "cluster": "cluster",
        "task_definition": "task-definition",
        "subnets": ["subnet"],
        "security_group": "sg",
        "log_group": "logs",
    }
    commands = Mock(
        side_effect=[
            json.dumps(config),
            json.dumps({"tasks": [{"taskArn": "task"}]}),
            json.dumps({"tasks": [{"containers": [{"exitCode": exit_code}]}]}),
        ]
    )
    monkeypatch.setattr(module.subprocess, "check_output", commands)
    wait = Mock()
    monkeypatch.setattr(module.subprocess, "run", wait)
    if exit_code == 0:
        module.run("schema")
    else:
        with pytest.raises(RuntimeError):
            module.run("schema")
    wait.assert_called_once()
    assert wait.call_args.kwargs["check"]


def test_ecs_task_start_failure_stops_release(monkeypatch, task_runner):
    module = task_runner
    config = {
        "region": "eu-west-2",
        "cluster": "cluster",
        "task_definition": "task",
        "subnets": [],
        "security_group": "sg",
    }
    monkeypatch.setattr(
        module.subprocess, "check_output", Mock(side_effect=[json.dumps(config), '{"failures":[{"reason":"DENIED"}]}'])
    )
    with pytest.raises(RuntimeError, match="Could not start"):
        module.run("schema")


def test_ecs_waiter_failure_requests_stop(monkeypatch, task_runner):
    module = task_runner
    config = {
        "region": "eu-west-2",
        "cluster": "cluster",
        "task_definition": "task",
        "subnets": [],
        "security_group": "sg",
        "log_group": "logs",
    }
    commands = Mock(side_effect=[json.dumps(config), '{"tasks":[{"taskArn":"task"}]}', "{}"])
    monkeypatch.setattr(module.subprocess, "check_output", commands)
    monkeypatch.setattr(module.subprocess, "run", Mock(side_effect=subprocess.CalledProcessError(1, "wait")))
    with pytest.raises(RuntimeError, match="stop requested"):
        module.run("schema")
    assert "stop-task" in commands.call_args.args[0]

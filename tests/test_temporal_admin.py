"""Admin releases fail closed, and bootstrap never overwrites an existing database schema."""

# ruff: noqa: S603, S607 # Tests execute fixed scripts with fake local commands, never AWS.

import os
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


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
  *"search-attribute create"*)
    count_file="$COMMAND_LOG.registration-count"
    count=0
    if [ -f "$count_file" ]; then count=$(cat "$count_file"); fi
    count=$((count + 1))
    printf '%s' "$count" > "$count_file"
    [ "$count" -gt "${SEARCH_ATTRIBUTE_FAILURES:-0}" ] || exit 1
    exit "${SEARCH_ATTRIBUTE_STATUS:-0}"
    ;;
esac
""",
        "sleep": "exit 0\n",
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
    assert "search-attribute" not in log.read_text()


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
    registrations = [line for line in log.read_text().splitlines() if "search-attribute create" in line]
    if result.returncode == 0:
        assert registrations == [
            "temporal operator search-attribute create -n default --address test-server:7233 "
            f"--name {name} --type Keyword"
            for name in ("UserId", "TranscriptionId", "MinuteId", "MinuteVersionId")
        ]
        assert log.read_text().index("search-attribute create") < log.read_text().index("namespace describe")
    else:
        assert not registrations


@pytest.mark.parametrize("failures", [1, 3])
def test_search_attribute_registration_retries_cold_start(admin_commands, failures):
    env, log = admin_commands
    subprocess.run(
        ["sh", "temporal-admin/entrypoint.sh", "namespace"],
        cwd=ROOT,
        env={**env, "SEARCH_ATTRIBUTE_FAILURES": str(failures)},
        check=True,
        capture_output=True,
    )
    commands = log.read_text().splitlines()
    registrations = [line for line in commands if "search-attribute create" in line]
    assert len(registrations) == failures + 4
    assert registrations[-1].endswith("--name MinuteVersionId --type Keyword")
    assert commands.count("sleep 1") == failures
    assert "namespace describe" in commands[-1]


@pytest.mark.parametrize("status", ["1", "2"])
def test_persistent_registration_failure_stops_namespace_task(admin_commands, status):
    env, log = admin_commands
    result = subprocess.run(
        ["sh", "temporal-admin/entrypoint.sh", "namespace"],
        cwd=ROOT,
        env={**env, "SEARCH_ATTRIBUTE_STATUS": status},
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode != 0
    assert "Could not register search attributes" in result.stderr
    commands = log.read_text().splitlines()
    assert sum("search-attribute create" in line for line in commands) == 10
    assert commands.count("sleep 1") == 9
    assert "namespace describe" not in log.read_text()


def test_existing_namespace_can_be_registered_again(admin_commands):
    env, log = admin_commands
    env = {**env, "NAMESPACES": '[{"namespaceInfo":{"name":"default"}}]'}
    for _ in range(2):
        subprocess.run(
            ["sh", "temporal-admin/entrypoint.sh", "namespace"], cwd=ROOT, env=env, check=True, capture_output=True
        )
    commands = log.read_text().splitlines()
    assert sum("search-attribute create" in line for line in commands) == 8
    assert "namespace create" not in log.read_text()

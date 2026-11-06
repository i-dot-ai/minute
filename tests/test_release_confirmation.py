"""Release selection and confirmation never create a tag for a different or unconfirmed SHA."""

# ruff: noqa: S603, S607 # Fixed commands use stubbed git/GitHub executables, never a real release.

import importlib.util
import json
import os
import re
import subprocess
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path
from unittest.mock import Mock

import pytest

ROOT = Path(__file__).resolve().parents[1]
SHA = "a" * 40
OLD_SHA = "b" * 40
PR = {
    "number": 2673,
    "state": "open",
    "head": {"ref": "feature/new", "sha": SHA, "repo": {"full_name": "i-dot-ai/minute"}},
}


@pytest.fixture
def release():
    spec = importlib.util.spec_from_file_location("release_confirmation", ROOT / ".github/scripts/release.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def gh(tmp_path):
    log = tmp_path / "commands"
    command = tmp_path / "gh"
    command.write_text(
        f"#!{sys.executable}\n"
        "import json, os, sys\n"
        "request = {'args': sys.argv[1:]}\n"
        "if '--input' in sys.argv:\n"
        "    request['body'] = json.load(sys.stdin)\n"
        "with open(os.environ['COMMAND_LOG'], 'a') as log:\n"
        "    log.write(json.dumps(request) + '\\n')\n"
        "path = sys.argv[2]\n"
        "responses = json.loads(os.environ['API_RESPONSES'])\n"
        "if path not in responses or os.environ.get('API_FAILURE'):\n"
        "    sys.exit('GitHub request failed')\n"
        "print(json.dumps(responses[path]))\n"
    )
    command.chmod(0o755)
    (tmp_path / "python3").symlink_to(sys.executable)
    git = tmp_path / "git"
    git.write_text(f'#!/bin/sh\nif [ "$2" = --abbrev-ref ]; then echo local-branch; else echo {SHA}; fi\n')
    git.chmod(0o755)
    responses = {
        "repos/i-dot-ai/minute/pulls/2673": PR,
        f"repos/i-dot-ai/minute/commits/{SHA}": {"sha": SHA},
        f"repos/i-dot-ai/minute/commits/{SHA}/pulls?per_page=100": [PR],
        f"repos/i-dot-ai/minute/commits/{OLD_SHA}/pulls?per_page=100": [
            {"number": 12, "head": {"ref": "feature/old", "sha": OLD_SHA}}
        ],
        "repos/i-dot-ai/minute/deployments?environment=dev&per_page=100&page=1": [
            {"id": 1, "ref": "main", "sha": OLD_SHA}
        ],
        "repos/i-dot-ai/minute/deployments/1/statuses?per_page=100": [
            {
                "state": "success",
                "created_at": "2026-11-05T12:34:56Z",
                "log_url": "https://github.com/i-dot-ai/minute/actions/runs/42/job/123",
            }
        ],
        "repos/i-dot-ai/minute/actions/runs/42": {
            "id": 42,
            "path": ".github/workflows/release.yml",
            "actor": {"login": "original-user"},
            "triggering_actor": {"login": "deploying-user"},
        },
        "repos/i-dot-ai/minute/actions/runs/42/jobs?per_page=100": {
            "total_count": 1,
            "jobs": [{"name": "build-temporal", "conclusion": "skipped"}],
        },
        "repos/i-dot-ai/minute/git/refs": {},
        "user": {"login": "operator"},
    }
    return {**os.environ, "PATH": f"{tmp_path}:{os.environ['PATH']}", "COMMAND_LOG": str(log)}, responses, log


def request(gh, args, answer="yes\n", **extra_env):
    env, responses, log = gh
    result = subprocess.run(
        ["make", *args],
        cwd=ROOT,
        env={**env, "API_RESPONSES": json.dumps(responses), **extra_env},
        input=answer,
        text=True,
        capture_output=True,
        check=False,
    )
    calls = [json.loads(line) for line in log.read_text().splitlines()] if log.exists() else []
    return result, calls


@pytest.mark.parametrize("target", ["release", "release-temporal-server"])
def test_pr_release_tags_confirmed_head_and_shows_previous_deployment(gh, target):
    _, responses, _ = gh
    if target == "release-temporal-server":
        responses["repos/i-dot-ai/minute/actions/runs/42/jobs?per_page=100"]["jobs"][0] = {
            "name": "build-temporal / build-image / Build and push to ECR",
            "conclusion": "success",
        }
    result, calls = request(gh, [target, "env=dev", "pr=2673"])
    assert result.returncode == 0, result.stderr
    write = calls[-1]
    prefix = "release-temporal-server" if target == "release-temporal-server" else "release"
    assert write["args"] == ["api", "repos/i-dot-ai/minute/git/refs", "--method", "POST", "--input", "-"]
    assert write["body"]["sha"] == SHA
    assert write["body"]["ref"].startswith(f"refs/tags/{prefix}-dev-pr-2673-operator-")
    for value in (
        "feature/new",
        "main",
        SHA,
        OLD_SHA[:7],
        "#2673",
        "#12",
        "deploying-user",
        "operator",
        "2026-11-05 12:34:56 UTC",
        "ago",
        "┌",
        "│",
        "┘",
    ):
        assert value in result.stdout
    assert "│ Field " not in result.stdout
    assert "main -> feature/new" in result.stdout
    assert "#12 -> #2673" in result.stdout
    assert "deploying-user -> operator" in result.stdout
    sha_row = next(line for line in result.stdout.splitlines() if line.startswith("│ SHA "))
    assert [cell.strip() for cell in sha_row.split("│")[1:-1]] == ["SHA", f"{OLD_SHA[:7]} -> {SHA[:7]}"]
    deployed_row = next(line for line in result.stdout.splitlines() if line.startswith("│ Deployed at "))
    assert "UTC (" in deployed_row
    assert "ago)" in deployed_row
    assert "->" not in deployed_row
    assert "How long ago" not in result.stdout
    assert result.stdout.index("│ Branch ") < result.stdout.index("Create release tag and deploy?")
    assert not any("git" in call["args"] for call in calls)


def test_no_pr_preserves_local_committed_revision(gh):
    result, calls = request(gh, ["release", "env=dev"])
    assert result.returncode == 0, result.stderr
    assert "local-branch" in result.stdout
    assert calls[-1]["body"]["sha"] == SHA
    assert calls[-1]["body"]["ref"].startswith("refs/tags/release-dev-local-branch-operator-")


@pytest.mark.parametrize("answer", ["", "\n", "no\n", "maybe\n"])
def test_cancel_and_eof_do_not_create_tag(gh, answer):
    result, calls = request(gh, ["release", "env=dev", "pr=2673"], answer)
    assert result.returncode == 0, result.stderr
    assert "Release cancelled" in result.stdout
    assert not any("body" in call for call in calls)


@pytest.mark.parametrize(
    "args",
    [
        ["release"],
        ["release", "env=prod", "pr=2673"],
        ["release", "env=invalid", "pr=2673"],
        ["release", "env=dev", "pr=0"],
        ["release", "env=dev", "pr=abc"],
        ["release", "env=dev", "pr=2673; touch bad-file"],
    ],
)
def test_invalid_arguments_never_call_github(gh, args):
    result, calls = request(gh, args)
    assert result.returncode != 0
    assert not calls


@pytest.mark.parametrize(
    "pr",
    [
        {**PR, "state": "closed"},
        {**PR, "head": {**PR["head"], "repo": None}},
        {**PR, "head": {**PR["head"], "repo": {"full_name": "someone/minute"}}},
        {**PR, "head": {**PR["head"], "sha": "invalid"}},
    ],
)
def test_unsafe_pr_never_prompts_or_creates_tag(gh, pr):
    _, responses, _ = gh
    responses["repos/i-dot-ai/minute/pulls/2673"] = pr
    result, calls = request(gh, ["release", "env=dev", "pr=2673"])
    assert result.returncode != 0
    assert "Create release tag" not in result.stdout
    assert not any("body" in call for call in calls)


def test_mismatched_commit_response_never_creates_tag(gh):
    _, responses, _ = gh
    responses[f"repos/i-dot-ai/minute/commits/{SHA}"] = {"sha": OLD_SHA}
    result, calls = request(gh, ["release", "env=dev", "pr=2673"])
    assert result.returncode != 0
    assert not any("body" in call for call in calls)


def test_github_error_fails_closed(gh):
    result, calls = request(gh, ["release", "env=dev", "pr=2673"], API_FAILURE="1")
    assert result.returncode != 0
    assert not any("body" in call for call in calls)


def test_first_release_displays_no_recorded_release(gh):
    _, responses, _ = gh
    responses["repos/i-dot-ai/minute/deployments?environment=preprod&per_page=100&page=1"] = []
    result, calls = request(gh, ["release", "env=preprod", "pr=2673"])
    assert result.returncode == 0, result.stderr
    assert "No recorded release" in result.stdout
    deployed_row = next(line for line in result.stdout.splitlines() if line.startswith("│ Deployed at "))
    assert [cell.strip() for cell in deployed_row.split("│")[1:-1]] == ["Deployed at", "-"]
    assert calls[-1]["body"]["ref"].startswith("refs/tags/release-preprod-pr-2673-")


def test_history_skips_failed_other_component_and_other_workflow_and_paginates(release, monkeypatch):
    responses = {
        "deployments?environment=dev&per_page=100&page=1": [
            {"id": 3, "ref": "main", "sha": SHA},
            {"id": 2, "ref": "release-temporal-server-dev-test-user-05-11-26--123456", "sha": SHA},
            {"id": 1, "ref": "main", "sha": SHA},
        ],
        "deployments/3/statuses?per_page=100": [{"state": "failure"}],
        "deployments/2/statuses?per_page=100": [
            {"state": "success", "log_url": "https://github.com/i-dot-ai/minute/actions/runs/2"}
        ],
        "actions/runs/2": {"id": 2, "path": ".github/workflows/release.yml"},
        "deployments/1/statuses?per_page=100": [
            {"state": "success", "log_url": "https://github.com/i-dot-ai/minute/actions/runs/1"}
        ],
        "actions/runs/1": {"id": 1, "path": ".github/workflows/release-public-site.yml"},
        "deployments?environment=dev&per_page=100&page=2": [
            {"id": 4, "ref": "release-dev-feature/old-test-user-05-11-26--123456", "sha": OLD_SHA}
        ],
        "deployments/4/statuses?per_page=100": [
            {
                "state": "inactive",
                "log_url": "https://github.com/i-dot-ai/minute/actions/runs/4",
            },
            {
                "state": "success",
                "created_at": "2026-11-05T12:34:56Z",
                "log_url": "https://github.com/i-dot-ai/minute/actions/runs/4",
            },
        ],
        "actions/runs/4": {"id": 4, "path": ".github/workflows/release.yml", "actor": {"login": "test-user"}},
        f"commits/{OLD_SHA}/pulls?per_page=100": [],
    }
    monkeypatch.setattr(release, "api", Mock(side_effect=responses.__getitem__))
    assert release.last_release("dev", "app") == {
        "branch": "feature/old",
        "sha": OLD_SHA,
        "pr": "—",
        "actor": "test-user",
        "deployed_at": "2026-11-05T12:34:56Z",
    }


def test_associated_pr_resolves_old_commits_and_does_not_guess_between_prs(release, monkeypatch):
    old_commit_pr = {**PR, "head": {**PR["head"], "sha": OLD_SHA}}
    api = Mock(return_value=[old_commit_pr])
    monkeypatch.setattr(release, "api", api)
    assert release.associated_pr(SHA) == old_commit_pr
    api.return_value = [old_commit_pr, {**old_commit_pr, "number": 2674}]
    assert release.associated_pr(SHA) is None


def test_pr_tag_preserves_history_after_pr_head_moves(gh):
    _, responses, _ = gh
    responses["repos/i-dot-ai/minute/deployments?environment=dev&per_page=100&page=1"][0]["ref"] = (
        "release-dev-pr-2673-operator-05-11-26--123456"
    )
    responses[f"repos/i-dot-ai/minute/commits/{OLD_SHA}/pulls?per_page=100"] = []
    result, calls = request(gh, ["release", "env=dev", "pr=2673"])
    assert result.returncode == 0, result.stderr
    pr_row = next(line for line in result.stdout.splitlines() if line.startswith("│ PR "))
    assert pr_row.count("#2673") == 2
    assert calls[-1]["body"]["sha"] == SHA


@pytest.mark.parametrize(
    ("seconds", "expected"),
    [(0, "0 seconds ago"), (1, "1 second ago"), (90, "1 minute ago"), (7200, "2 hours ago"), (172800, "2 days ago")],
)
def test_deployment_time_is_utc_and_relative(release, seconds, expected):
    now = datetime(2026, 11, 6, 12, tzinfo=UTC)
    timestamp = (now - timedelta(seconds=seconds)).isoformat()
    exact, age = release.deployment_time(timestamp, now)
    assert exact.endswith("UTC")
    assert age == expected
    assert release.deployment_time("2026-11-06T13:00:00+01:00", now) == ("2026-11-06 12:00:00 UTC", "0 seconds ago")


def test_keyboard_interrupt_cancels(release, monkeypatch):
    monkeypatch.setattr("builtins.input", Mock(side_effect=KeyboardInterrupt))
    assert release.confirm("dev", "app", None, {"branch": "main", "sha": SHA, "pr": "—"}, "operator") is False


@pytest.mark.parametrize(
    ("tty", "no_color", "term", "colored"),
    [
        (True, False, "xterm-256color", True),
        (False, False, "xterm", False),
        (True, True, "xterm", False),
        (True, False, "dumb", False),
    ],
)
def test_table_color_is_optional_and_preserves_alignment(release, monkeypatch, capsys, tty, no_color, term, colored):
    monkeypatch.setattr(release.sys.stdout, "isatty", lambda: tty)
    monkeypatch.setenv("TERM", term)
    if no_color:
        monkeypatch.setenv("NO_COLOR", "")
    else:
        monkeypatch.delenv("NO_COLOR", raising=False)
    monkeypatch.setattr("builtins.input", lambda _prompt: "no")
    current = {
        "branch": "main",
        "sha": OLD_SHA,
        "pr": "#12",
        "actor": "previous",
        "deployed_at": "2026-11-05T12:34:56Z",
    }
    proposed = {"branch": "feature/new", "sha": SHA, "pr": "#2673"}
    assert release.confirm("dev", "app", current, proposed, "operator") is False
    output = capsys.readouterr().out
    assert ("\033[" in output) is colored
    if colored:
        assert "\033[33mmain\033[0m -> \033[32mfeature/new\033[0m" in output
        assert "\033[1;36mBranch" in output
        assert "\033[90m2026-11-05 12:34:56 UTC (" in output
    plain = re.sub(r"\x1b\[[0-9;]*m", "", output)
    table = [line for line in plain.splitlines() if line.startswith(("┌", "│", "└"))]
    assert len({len(line) for line in table}) == 1
    assert "main -> feature/new" in plain


def test_pr_head_is_resolved_only_once_before_confirmation(gh):
    result, calls = request(gh, ["release", "env=dev", "pr=2673"])
    assert result.returncode == 0, result.stderr
    assert sum(call["args"] == ["api", "repos/i-dot-ai/minute/pulls/2673"] for call in calls) == 1
    assert calls[-1]["body"]["sha"] == SHA

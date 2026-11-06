"""Confirm a published revision against GitHub's release history before creating its release tag."""

# ruff: noqa: S603, S607, T201 # This CLI executes git/gh with argument lists and prints its confirmation.

import argparse
import json
import os
import re
import subprocess
import sys
from datetime import UTC, datetime

REPO = "i-dot-ai/minute"
SHA = re.compile(r"[0-9a-f]{40}")
PAGE_SIZE = 100


def api(path: str):
    return json.loads(subprocess.check_output(["gh", "api", f"repos/{REPO}/{path}"], text=True))


def associated_pr(sha: str):
    prs = api(f"commits/{sha}/pulls?per_page={PAGE_SIZE}")
    matches = [pr for pr in prs if pr["head"]["sha"] == sha or pr.get("merge_commit_sha") == sha]
    if not matches:
        matches = prs
    return matches[0] if len(matches) == 1 else None


def proposed_release(pr_number: str) -> dict:
    if pr_number:
        if not re.fullmatch(r"[1-9][0-9]*", pr_number):
            msg = "pr must be a positive PR number"
            raise ValueError(msg)
        pr = api(f"pulls/{pr_number}")
        if pr["state"] != "open" or not pr["head"]["repo"] or pr["head"]["repo"]["full_name"] != REPO:
            msg = "Only open, same-repository PRs can be released; fork PRs are not allowed"
            raise ValueError(msg)
        branch, sha = pr["head"]["ref"], pr["head"]["sha"]
    else:
        branch = subprocess.check_output(["git", "rev-parse", "--abbrev-ref", "HEAD"], text=True).strip()
        sha = subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
        pr = None
    if not SHA.fullmatch(sha) or api(f"commits/{sha}")["sha"] != sha:
        msg = "The selected SHA must be a published Minute commit; commit and push first"
        raise ValueError(msg)
    if not pr_number:
        pr = associated_pr(sha)
    return {"branch": branch, "sha": sha, "pr": f"#{pr['number']}" if pr else "—"}


def release_component(ref: str, run_id: int) -> str:
    if ref.startswith("release-temporal-server-"):
        return "temporal-server"
    if ref.startswith(("release-dev-", "release-preprod-")):
        return "app"
    jobs = api(f"actions/runs/{run_id}/jobs?per_page={PAGE_SIZE}")
    if jobs["total_count"] > PAGE_SIZE:
        msg = "Cannot identify release component from paginated jobs"
        raise ValueError(msg)
    return (
        "temporal-server"
        if any(
            job["name"].split(" / ")[0] == "build-temporal" and job["conclusion"] != "skipped" for job in jobs["jobs"]
        )
        else "app"
    )


def last_release(environment: str, component: str):
    # shortcut: GitHub history cannot detect out-of-band AWS changes; use ECS inspection when that is needed.
    page = 1
    while deployments := api(f"deployments?environment={environment}&per_page={PAGE_SIZE}&page={page}"):
        for deployment in deployments:
            statuses = api(f"deployments/{deployment['id']}/statuses?per_page={PAGE_SIZE}")
            success = next((status for status in statuses if status["state"] == "success"), None)
            if not success:
                continue
            match = re.search(rf"github\.com/{re.escape(REPO)}/actions/runs/(\d+)", success.get("log_url", ""))
            if not match:
                continue
            run = api(f"actions/runs/{match[1]}")
            if run["path"].split("@")[0] != ".github/workflows/release.yml":
                continue
            ref = deployment["ref"]
            if release_component(ref, run["id"]) != component:
                continue
            tagged_pr = re.match(r"release-(?:temporal-server-)?(?:dev|preprod)-pr-([1-9][0-9]*)-", ref)
            pr = api(f"pulls/{tagged_pr[1]}") if tagged_pr else associated_pr(deployment["sha"])
            actor = (run.get("triggering_actor") or run["actor"])["login"]
            branch = ref
            if ref.startswith("release-"):
                if tagged_pr:
                    branch = pr["head"]["ref"]
                else:
                    prefix = f"release-{'temporal-server-' if component == 'temporal-server' else ''}{environment}-"
                    branch = re.sub(
                        rf"-(?:{re.escape(actor)}|[^-]+)-\d{{2}}-\d{{2}}-\d{{2}}--\d{{6}}$",
                        "",
                        ref.removeprefix(prefix),
                    )
            return {
                "branch": branch,
                "sha": deployment["sha"],
                "pr": f"#{pr['number']}" if pr else "—",
                "actor": actor,
                "deployed_at": success["created_at"],
            }
        page += 1
    return None


def deployment_time(timestamp: str, now: datetime) -> tuple[str, str]:
    deployed = datetime.fromisoformat(timestamp).astimezone(UTC)
    seconds = max(0, int((now - deployed).total_seconds()))
    for size, label in ((86400, "day"), (3600, "hour"), (60, "minute")):
        if seconds >= size:
            count = seconds // size
            age = f"{count} {label}{'s' if count != 1 else ''} ago"
            break
    else:
        age = f"{seconds} second{'s' if seconds != 1 else ''} ago"
    return deployed.strftime("%Y-%m-%d %H:%M:%S UTC"), age


def confirm(environment: str, component: str, current: dict | None, proposed: dict, actor: str) -> bool:
    timestamp, age = deployment_time(current["deployed_at"], datetime.now(UTC)) if current else ("—", "—")
    rows = [
        ("Branch", f"{current['branch'] if current else 'No recorded release'} -> {proposed['branch']}"),
        ("SHA", f"{current['sha'][:7] if current else '—'} -> {proposed['sha'][:7]}"),
        ("PR", f"{current['pr'] if current else '—'} -> {proposed['pr']}"),
        ("Released by", f"{current['actor'] if current else '—'} -> {actor}"),
        ("Deployed at", f"{timestamp} ({age})" if current else "-"),
    ]
    rows = [tuple(" ".join(value.split()) for value in row) for row in rows]
    widths = [max(len(row[column]) for row in rows) for column in range(2)]
    use_color = sys.stdout.isatty() and "NO_COLOR" not in os.environ and os.environ.get("TERM") != "dumb"

    def color(text: str, code: str) -> str:
        return f"\033[{code}m{text}\033[0m" if use_color else text

    def border(left: str, middle: str, right: str) -> None:
        print(color(left + middle.join("─" * (width + 2) for width in widths) + right, "90"))

    print(color(f"\nRelease {component} to {environment}", "1;36"))
    border("┌", "┬", "┐")
    for label, value in rows:
        padding = " " * (widths[1] - len(value))
        if label == "Deployed at":
            rendered = color(value, "90")
        else:
            old, _, new = value.partition(" -> ")
            rendered = color(old, "33") + " -> " + color(new, "32")
        print(f"│ {color(f'{label:<{widths[0]}}', '1;36')} │ {rendered}{padding} │")
    border("└", "┴", "┘")
    print("GitHub history is the last successful recorded release, not a live AWS inventory.")
    try:
        return input("Create release tag and deploy? [y/N]: ").strip().lower() in ("y", "yes")
    except (EOFError, KeyboardInterrupt):
        return False


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("environment", choices=("dev", "preprod"))
    parser.add_argument("component", choices=("app", "temporal-server"), nargs="?", default="app")
    parser.add_argument("pr", nargs="?", default=os.environ.get("RELEASE_PR", ""))
    args = parser.parse_args()
    proposed = proposed_release(args.pr)
    current = last_release(args.environment, args.component)
    actor = json.loads(subprocess.check_output(["gh", "api", "user"], text=True))["login"]
    if not confirm(args.environment, args.component, current, proposed, actor):
        print("Release cancelled. No tag created or deployment requested.")
        return
    prefix = "release" if args.component == "app" else "release-temporal-server"
    source = f"pr-{args.pr}" if args.pr else proposed["branch"]
    tag = f"{prefix}-{args.environment}-{source}-{actor}-{datetime.now(UTC):%d-%m-%y--%H%M%S}"
    # Creating the lightweight tag remotely pins the confirmed SHA without changing the local checkout.
    subprocess.run(
        ["gh", "api", f"repos/{REPO}/git/refs", "--method", "POST", "--input", "-"],
        input=json.dumps({"ref": f"refs/tags/{tag}", "sha": proposed["sha"]}),
        text=True,
        capture_output=True,
        check=True,
    )
    print(f"Requested {args.component} release to {args.environment}: {tag} at {proposed['sha']}")
    print(f"https://github.com/{REPO}/actions/workflows/release.yml")


if __name__ == "__main__":
    try:
        main()
    except (ValueError, KeyError, OSError, subprocess.CalledProcessError) as error:
        detail = error.stderr if isinstance(error, subprocess.CalledProcessError) and error.stderr else str(error)
        message = f"Release failed: {detail}"
        raise SystemExit(message) from error

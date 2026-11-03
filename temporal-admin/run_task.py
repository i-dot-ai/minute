"""Run an admin task and require an exit code of zero before the release continues."""

# ruff: noqa: S603, S607 # Fixed executables and argv, no shell; task configuration comes from Terraform.

import json
import subprocess
import sys


def run(mode: str) -> None:
    config = json.loads(
        subprocess.check_output(
            ["terraform", "-chdir=terraform-temporal", "output", "-json", "temporal_admin"], text=True
        )
    )

    def aws(*args: str) -> dict:
        return json.loads(
            subprocess.check_output(["aws", "--region", config["region"], "ecs", *args, "--output", "json"], text=True)
        )

    result = aws(
        "run-task",
        "--cluster",
        config["cluster"],
        "--task-definition",
        config["task_definition"],
        "--launch-type",
        "FARGATE",
        "--network-configuration",
        json.dumps(
            {
                "awsvpcConfiguration": {
                    "subnets": config["subnets"],
                    "securityGroups": [config["security_group"]],
                    "assignPublicIp": "DISABLED",
                }
            }
        ),
        "--overrides",
        json.dumps({"containerOverrides": [{"name": "temporal-admin", "command": [mode]}]}),
    )
    if result.get("failures") or len(result.get("tasks", [])) != 1:
        msg = f"Could not start Temporal admin task: {result}"
        raise RuntimeError(msg)
    task = result["tasks"][0]["taskArn"]
    print(f"Temporal {mode} task: {task}; logs: {config['log_group']}", flush=True)  # noqa: T201
    try:
        subprocess.run(
            [
                "aws",
                "--region",
                config["region"],
                "ecs",
                "wait",
                "tasks-stopped",
                "--cluster",
                config["cluster"],
                "--tasks",
                task,
            ],
            check=True,
        )
    except subprocess.CalledProcessError as error:
        # Do not leave a migration running past the release lock or retry it concurrently.
        aws("stop-task", "--cluster", config["cluster"], "--task", task, "--reason", "Temporal admin waiter failed")
        msg = f"Temporal {mode} waiter failed; task stop requested. Inspect {config['log_group']} before retrying"
        raise RuntimeError(msg) from error
    stopped = aws("describe-tasks", "--cluster", config["cluster"], "--tasks", task)
    tasks = stopped.get("tasks", [])
    if stopped.get("failures") or len(tasks) != 1:
        msg = f"Could not inspect Temporal admin task: {stopped}"
        raise RuntimeError(msg)
    containers = tasks[0].get("containers", [])
    if len(containers) != 1 or containers[0].get("exitCode") != 0:
        msg = f"Temporal {mode} failed: {tasks[0].get('stoppedReason')}; {containers}. See {config['log_group']}"
        raise RuntimeError(msg)


if __name__ == "__main__":
    if len(sys.argv) != 2 or sys.argv[1] not in ("schema", "namespace"):  # noqa: PLR2004
        sys.exit("Usage: run_task.py <schema|namespace>")
    run(sys.argv[1])

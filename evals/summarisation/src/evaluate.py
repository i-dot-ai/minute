from __future__ import annotations

import sys
from pathlib import Path

import typer

from evals.summarisation.src.config import load_config
from evals.summarisation.src.runner import run_eval

WORKDIR = Path(__file__).resolve().parent.parent
DEFAULT_CONFIG = WORKDIR / "configs" / "smoke-test.yaml"

app = typer.Typer()

config_path_arg = typer.Option(DEFAULT_CONFIG, "--config", exists=True, dir_okay=False, readable=True)


@app.callback(invoke_without_command=True)
def run(
    config: Path = config_path_arg,
) -> None:
    cfg = load_config(config)
    run_id, results_path, summary_path = run_eval(
        cfg,
        split=cfg.run.split,
        limit=cfg.run.limit,
        prompt_version=cfg.run.prompt_version,
    )

    typer.echo(f"run_id={run_id}")
    typer.echo(f"results={results_path}")
    typer.echo(f"summary={summary_path}")


if __name__ == "__main__":
    sys.exit(app())

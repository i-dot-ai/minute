from __future__ import annotations

from pathlib import Path

import typer

from .config import load_config
from .runner import run_eval

app = typer.Typer(no_args_is_help=True)


@app.command()
def run(
    config: Path = typer.Option(..., "--config", exists=True, dir_okay=False, readable=True),
    split: str = typer.Option("test", "--split"),
    limit: int | None = typer.Option(None, "--limit"),
    prompt_version: str = typer.Option("dev", "--prompt-version"),
) -> None:
    cfg = load_config(config)
    run_id, results_path, summary_path = run_eval(
        cfg,
        split=split,
        limit=limit,
        prompt_version=prompt_version,
    )

    typer.echo(f"run_id={run_id}")
    typer.echo(f"results={results_path}")
    typer.echo(f"summary={summary_path}")

from __future__ import annotations

from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, Field

type MetricName = Literal[
    "faithfulness",
    "coverage",
    "conciseness",
    "coherence",
]


def default_criteria() -> list[MetricName]:
    return ["faithfulness", "coverage", "conciseness", "coherence"]


class RunConfig(BaseModel):
    output_dir: str = "runs"
    seed: int = 0
    split: str = "test"
    limit: int | None = None
    prompt_version: str = "dev"


class DatasetConfig(BaseModel):
    name: str
    config: str | None = None
    dialogue_field: str = "dialogue"
    reference_summary_field: str = "summary"


class JudgeConfig(BaseModel):
    pass_threshold: int = 4


class PromptConfig(BaseModel):
    summarizer_template_path: str
    judge_template_path: str


class AppConfig(BaseModel):
    run: RunConfig
    dataset: DatasetConfig
    judge: JudgeConfig
    metrics: list[MetricName] = Field(default_factory=default_criteria)
    prompts: PromptConfig


def load_config(path: str | Path) -> AppConfig:
    path = Path(path)
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    return AppConfig.model_validate(data)

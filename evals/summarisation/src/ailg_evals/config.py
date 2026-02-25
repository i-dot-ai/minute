from __future__ import annotations

import os
from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, Field


class RunConfig(BaseModel):
    output_dir: str = "runs"
    seed: int = 0


class DatasetConfig(BaseModel):
    name: str
    config: str | None = None
    dialogue_field: str = "dialogue"
    reference_summary_field: str = "summary"


class ModelConfig(BaseModel):
    base_url: str
    api_key_env: str = "OPENAI_API_KEY"
    model: str
    temperature: float = 0.2
    max_tokens: int = 256
    timeout_s: int = 120

    @property
    def api_key(self) -> str:
        key = os.getenv(self.api_key_env, "")
        # Some servers ignore API keys, but the client may still require a value.
        return key or "lm-studio"


class JudgeConfig(ModelConfig):
    pass_threshold: int = 4
    criteria: list[Literal["faithfulness", "coverage", "conciseness", "coherence"]] = Field(
        default_factory=lambda: ["faithfulness", "coverage", "conciseness", "coherence"]
    )


class PromptConfig(BaseModel):
    summarizer_template_path: str
    judge_template_path: str


class AppConfig(BaseModel):
    run: RunConfig
    dataset: DatasetConfig
    model: ModelConfig
    judge: JudgeConfig
    metrics: list[str] = Field(default_factory=list)
    prompts: PromptConfig


def load_config(path: str | Path) -> AppConfig:
    path = Path(path)
    data = yaml.safe_load(path.read_text(encoding="utf-8"))

    # Convenience: allow judge config to omit ModelConfig fields when it shares the same endpoint.
    # Since JudgeConfig subclasses ModelConfig, we backfill required fields prior to validation.
    if isinstance(data, dict):
        model_cfg = data.get("model")
        judge_cfg = data.get("judge")
        if isinstance(model_cfg, dict) and isinstance(judge_cfg, dict):
            judge_cfg.setdefault("base_url", model_cfg.get("base_url"))
            judge_cfg.setdefault("api_key_env", model_cfg.get("api_key_env"))
    cfg = AppConfig.model_validate(data)

    # Allow env override for base_url without changing YAML.
    env_base_url = os.getenv("AILG_EVALS_BASE_URL")
    if env_base_url:
        cfg.model.base_url = env_base_url

    return cfg

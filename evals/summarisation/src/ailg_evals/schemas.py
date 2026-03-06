from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class DialogExample(BaseModel):
    example_id: str
    dialogue: str
    reference_summary: str | None = None


class GenerationConfig(BaseModel):
    temperature: float
    max_tokens: int


class DialogSummary(BaseModel):
    summary: str
    model: str
    prompt_version: str
    generation_config: GenerationConfig


CriteriaName = Literal["faithfulness", "coverage", "conciseness", "coherence"]


class MetricResult(BaseModel):
    score: float = Field(ge=0.0, le=1.0)
    reason: str


class EvalRecord(BaseModel):
    run_id: str
    timestamp: datetime
    example: DialogExample
    candidate: DialogSummary
    metrics: dict[str, MetricResult]
    latency_ms: dict[str, int]
    error: dict[str, str] | None = None

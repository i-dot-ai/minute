from __future__ import annotations

from dataclasses import dataclass

import dspy

from .config import AppConfig
from .schemas import DialogExample, MetricResult
from .signatures import JudgeRatingSignature


@dataclass(frozen=True)
class DialogSummaryMetric:
    name: str
    criterion: str
    pass_threshold: int
    lm: dspy.LM

    def evaluate(
        self,
        *,
        example: DialogExample,
        prediction: dspy.Prediction,
    ) -> MetricResult:
        with dspy.context(lm=self.lm):
            pred = dspy.Predict(JudgeRatingSignature)(
                dialogue=example.dialogue,
                reference_summary=example.reference_summary,
                candidate_summary=prediction.summary,
                criterion=self.criterion,
            )

        rating = int(pred.rating)
        passed = rating >= self.pass_threshold
        return MetricResult(
            score=1.0 if passed else 0.0,
            reason=f"rating={rating} threshold={self.pass_threshold} :: {pred.reason}",
        )


def build_metrics(cfg: AppConfig) -> list[DialogSummaryMetric]:
    metrics: list[DialogSummaryMetric] = []

    judge_lm = dspy.LM(
        cfg.judge.model,
        api_base=cfg.judge.base_url,
        api_key=cfg.judge.api_key,
        temperature=cfg.judge.temperature,
        max_tokens=cfg.judge.max_tokens,
    )

    for name in cfg.metrics:
        metrics.append(
            DialogSummaryMetric(
                name=f"judge_{name}",
                criterion=name,
                pass_threshold=cfg.judge.pass_threshold,
                lm=judge_lm,
            )
        )
    return metrics

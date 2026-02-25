from __future__ import annotations

import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

import dspy
import orjson
from datasets import load_dataset
from dspy.evaluate import Evaluate
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from tenacity import retry, stop_after_attempt, wait_exponential

from .config import AppConfig, ModelConfig
from .jsonl import write_jsonl
from .metric import DialogSummaryMetric, build_metrics
from .prompts import render_template
from .schemas import (
    DialogExample,
    DialogSummary,
    EvalRecord,
    GenerationConfig,
    MetricResult,
)


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _ms(start_s: float, end_s: float) -> int:
    return int(round((end_s - start_s) * 1000))


def _prepare_run_paths(cfg: AppConfig, run_id: str) -> tuple[Path, Path, Path]:
    out_dir = Path(cfg.run.output_dir) / run_id
    out_dir.mkdir(parents=True, exist_ok=True)

    results_path = out_dir / "results.jsonl"
    summary_path = out_dir / "summary.json"
    return out_dir, results_path, summary_path


def _load_data_pairs(cfg: AppConfig, *, split: str, limit: int | None) -> list[DialogExample]:
    ds = load_dataset(cfg.dataset.name, cfg.dataset.config)
    rows = ds[split]
    if limit is not None:
        rows = rows.select(range(min(limit, len(rows))))

    examples: list[DialogExample] = []
    for i, row in enumerate(rows):
        ex = DialogExample(
            example_id=str(row.get("id", i)),
            dialogue=row[cfg.dataset.dialogue_field],
            reference_summary=row.get(cfg.dataset.reference_summary_field),
        )
        examples.append(ex)
    return examples


def _to_dspy_devset(examples: list[DialogExample]) -> list[dspy.Example]:
    devset: list[dspy.Example] = []
    for ex in examples:
        devset.append(
            dspy.Example(
                example_id=ex.example_id,
                dialogue=ex.dialogue,
                reference_summary=ex.reference_summary,
            ).with_inputs("dialogue")
        )
    return devset


@retry(stop=stop_after_attempt(2), wait=wait_exponential(multiplier=2, min=1, max=60))
def _build_llm(model_cfg: ModelConfig) -> ChatOpenAI:
    return ChatOpenAI(
        base_url=model_cfg.base_url,
        api_key=model_cfg.api_key,
        model=model_cfg.model,
        temperature=model_cfg.temperature,
        max_tokens=model_cfg.max_tokens,
        timeout=model_cfg.timeout_s,
    )


def _build_prompts() -> tuple[ChatPromptTemplate, ChatPromptTemplate]:
    summarize_prompt = ChatPromptTemplate.from_messages([("user", "{text}")])
    judge_prompt = ChatPromptTemplate.from_messages([("user", "{text}")])
    return summarize_prompt, judge_prompt


def _summarize_one(
    *,
    cfg: AppConfig,
    summarizer_llm: ChatOpenAI,
    summarize_prompt: ChatPromptTemplate,
    summarizer_template_path: str,
    dialogue: str,
    prompt_version: str,
) -> tuple[DialogSummary, int]:
    t0 = time.perf_counter()
    summarize_text = render_template(summarizer_template_path, dialogue=dialogue)
    summarize_msg = summarize_prompt.invoke({"text": summarize_text})
    summary_resp = summarizer_llm.invoke(summarize_msg)
    t1 = time.perf_counter()

    candidate = DialogSummary(
        summary=summary_resp.content.strip(),
        model=cfg.model.model,
        prompt_version=prompt_version,
        generation_config=GenerationConfig(
            temperature=cfg.model.temperature,
            max_tokens=cfg.model.max_tokens,
        ),
    )
    return candidate, _ms(t0, t1)


def _evaluate_metrics(
    *,
    metrics: Iterable[DialogSummaryMetric],
    example: DialogExample,
    prediction: dspy.Prediction,
) -> dict[str, MetricResult]:
    out: dict[str, MetricResult] = {}
    for m in metrics:
        out[m.name] = m.evaluate(example=example, prediction=prediction)
    return out


def _maybe_flush_records(
    results_path: Path, records: list[dict[str, Any]], *, flush_every: int
) -> None:
    if len(records) >= flush_every:
        write_jsonl(results_path, records)
        records.clear()


def _p50(values: list[int]) -> int:
    if not values:
        return 0
    values_sorted = sorted(values)
    return int(values_sorted[len(values_sorted) // 2])


def run_eval(
    cfg: AppConfig,
    *,
    split: str,
    limit: int | None,
    prompt_version: str,
) -> tuple[str, Path, Path]:
    run_id = str(uuid.uuid4())
    _, results_path, summary_path = _prepare_run_paths(cfg, run_id)

    examples = _load_data_pairs(cfg, split=split, limit=limit)
    devset = _to_dspy_devset(examples)

    summarizer_llm = _build_llm(cfg.model)

    summarizer_template_path = cfg.prompts.summarizer_template_path

    metrics = build_metrics(cfg)
    summarize_prompt, _ = _build_prompts()

    records: list[dict[str, Any]] = []
    summarize_ms_values: list[int] = []
    judge_ms_values: list[int] = []
    metric_names = [m.name for m in metrics]
    metric_scores: dict[str, list[float]] = {name: [] for name in metric_names}

    class _Program:
        def __call__(self, *, dialogue: str):
            candidate, summarize_ms = _summarize_one(
                cfg=cfg,
                summarizer_llm=summarizer_llm,
                summarize_prompt=summarize_prompt,
                summarizer_template_path=summarizer_template_path,
                dialogue=dialogue,
                prompt_version=prompt_version,
            )
            summarize_ms_values.append(summarize_ms)
            return dspy.Prediction(summary=candidate.summary, _candidate=candidate)

    program = _Program()

    def _metric(gold, pred, trace=None):
        ex = DialogExample(
            example_id=str(getattr(gold, "example_id")),
            dialogue=str(getattr(gold, "dialogue")),
            reference_summary=getattr(gold, "reference_summary", None),
        )

        t_j0 = time.perf_counter()
        metrics_out = _evaluate_metrics(metrics=metrics, example=ex, prediction=pred)
        t_j1 = time.perf_counter()
        judge_ms = _ms(t_j0, t_j1)
        judge_ms_values.append(judge_ms)

        for name, res in metrics_out.items():
            metric_scores[name].append(res.score)

        candidate = getattr(pred, "_candidate")
        rec = EvalRecord(
            run_id=run_id,
            timestamp=_now(),
            example=ex,
            candidate=candidate,
            metrics=metrics_out,
            latency_ms={
                "summarize": summarize_ms_values[-1] if summarize_ms_values else 0,
                "judge": judge_ms,
            },
            error=None,
        )
        records.append(rec.model_dump(by_alias=True))
        _maybe_flush_records(results_path, records, flush_every=25)

        # Return a scalar score for DSPy evaluation.
        if metric_names:
            return float(sum(metrics_out[n].score for n in metric_names) / len(metric_names))
        return 0.0

    evaluator = Evaluate(devset=devset, num_threads=1, display_progress=True, display_table=5)
    overall_score = evaluator(program, metric=_metric)

    if records:
        write_jsonl(results_path, records)

    metrics_summary = {
        name: {"mean": float(sum(vals) / len(vals)) if vals else 0.0}
        for name, vals in metric_scores.items()
    }
    summary = {
        "run_id": run_id,
        "split": split,
        "n": len(devset),
        "overall": float(overall_score) if overall_score is not None else None,
        "metrics": metrics_summary,
        "latency_ms": {
            "summarize_p50": _p50(summarize_ms_values),
            "judge_p50": _p50(judge_ms_values),
        },
    }

    summary_path.write_bytes(orjson.dumps(summary, option=orjson.OPT_INDENT_2))
    return run_id, results_path, summary_path

from __future__ import annotations

import json
from datetime import UTC, datetime

import pytest

from evals.summarisation.src.schemas import (
    DialogExample,
    DialogSummary,
    EvalRecord,
    GenerationConfig,
    MetricResult,
)


def test_metric_result_contract_validates_score_bounds():
    """CONTRACT TEST: MetricResult enforces score must be between 0.0 and 1.0."""
    with pytest.raises(ValueError, match="less than or equal to 1"):
        MetricResult(score=1.5, reason="Invalid")

    with pytest.raises(ValueError, match="greater than or equal to 0"):
        MetricResult(score=-0.1, reason="Invalid")

    valid = MetricResult(score=0.5, reason="Valid")
    assert valid.score == 0.5


def test_eval_record_contract_serializes_to_json():
    """CONTRACT TEST: EvalRecord can be serialized to JSON for storage in JSONL files."""
    example_id = "1"
    model_name = "gpt-4"
    run_id = "test_run"
    faithfulness_score = 0.8

    example = DialogExample(example_id=example_id, dialogue="Hello", reference_summary="Hi")
    candidate = DialogSummary(
        summary="Summary",
        model=model_name,
        prompt_version="v1",
        generation_config=GenerationConfig(temperature=0.2, max_tokens=256),
    )
    metrics = {"faithfulness": MetricResult(score=faithfulness_score, reason="Good")}

    record = EvalRecord(
        run_id=run_id,
        timestamp=datetime.now(UTC),
        example=example,
        candidate=candidate,
        metrics=metrics,
        latency_ms={"summarize": 1000, "judge": 500},
        error=None,
    )

    serialized = record.model_dump(mode="json")
    json_str = json.dumps(serialized)
    deserialized = json.loads(json_str)

    assert deserialized["run_id"] == run_id
    assert deserialized["example"]["example_id"] == example_id
    assert deserialized["candidate"]["model"] == model_name
    assert deserialized["metrics"]["faithfulness"]["score"] == faithfulness_score


def test_eval_record_contract_handles_optional_reference_summary():
    """CONTRACT TEST: DialogExample allows optional reference_summary for datasets without ground truth."""
    reference_text = "Greeting"

    example_without_ref = DialogExample(example_id="1", dialogue="Hello")
    example_with_ref = DialogExample(example_id="2", dialogue="Hi", reference_summary=reference_text)

    assert example_without_ref.reference_summary is None
    assert example_with_ref.reference_summary == reference_text

    serialized_without = example_without_ref.model_dump()
    serialized_with = example_with_ref.model_dump()

    assert "reference_summary" in serialized_without
    assert serialized_without["reference_summary"] is None
    assert serialized_with["reference_summary"] == reference_text


def test_eval_record_contract_handles_errors():
    """CONTRACT TEST: EvalRecord can store error information when evaluation fails."""
    model_name = "gpt-4"
    run_id = "test_run"
    error_type = "APIError"

    example = DialogExample(example_id="1", dialogue="Test")
    candidate = DialogSummary(
        summary="",
        model=model_name,
        prompt_version="v1",
        generation_config=GenerationConfig(temperature=0.2, max_tokens=256),
    )

    record_with_error = EvalRecord(
        run_id=run_id,
        timestamp=datetime.now(UTC),
        example=example,
        candidate=candidate,
        metrics={},
        latency_ms={},
        error={"type": error_type, "message": "Rate limit exceeded"},
    )

    record_without_error = EvalRecord(
        run_id=run_id,
        timestamp=datetime.now(UTC),
        example=example,
        candidate=candidate,
        metrics={},
        latency_ms={},
        error=None,
    )

    assert record_with_error.error["type"] == error_type
    assert record_without_error.error is None


def test_generation_config_contract_preserves_llm_parameters():
    """CONTRACT TEST: GenerationConfig preserves LLM generation parameters for reproducibility."""
    config = GenerationConfig(temperature=0.7, max_tokens=512)

    serialized = config.model_dump()
    deserialized = GenerationConfig(**serialized)

    assert deserialized.temperature == 0.7
    assert deserialized.max_tokens == 512

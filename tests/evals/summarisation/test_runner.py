from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import dspy

from evals.summarisation.src.config import AppConfig
from evals.summarisation.src.runner import (
    _load_data_pairs,
    _ms,
    _now,
    _p50,
    _prepare_run_paths,
    _to_dspy_devset,
    run_eval,
)
from evals.summarisation.src.schemas import DialogExample


def test_now_returns_utc_datetime():
    result = _now()
    assert isinstance(result, datetime)
    assert result.tzinfo == UTC


def test_ms_converts_seconds_to_milliseconds():
    start = 1.0
    end = 1.5
    result = _ms(start, end)
    assert result == 500


def test_ms_rounds_correctly():
    start = 1.0
    end = 1.0006
    result = _ms(start, end)
    assert result == 1


def test_p50_empty_list():
    assert _p50([]) == 0


def test_p50_single_value():
    assert _p50([100]) == 100


def test_p50_odd_count():
    values = [10, 20, 30, 40, 50]
    assert _p50(values) == 30


def test_p50_even_count():
    values = [10, 20, 30, 40]
    assert _p50(values) == 30


def test_p50_unsorted_input():
    values = [50, 10, 30, 20, 40]
    assert _p50(values) == 30


def test_prepare_run_paths_creates_directories(tmp_path):
    cfg = AppConfig.model_validate(
        {
            "run": {"output_dir": str(tmp_path / "output")},
            "dataset": {"name": "test"},
            "judge": {"pass_threshold": 4},
            "prompts": {
                "summarizer_template_path": "prompts/summarizer.jinja2",
                "judge_template_path": "prompts/judge.jinja2",
            },
        }
    )
    run_id = "test-run-123"

    out_dir, results_path, summary_path = _prepare_run_paths(cfg, run_id)

    assert out_dir.exists()
    assert out_dir == tmp_path / "output" / run_id
    assert results_path == out_dir / "results.jsonl"
    assert summary_path == out_dir / "summary.json"


def test_load_data_pairs_basic():
    cfg = AppConfig.model_validate(
        {
            "run": {"output_dir": "output"},
            "dataset": {
                "name": "test_dataset",
                "dialogue_field": "dialogue",
                "reference_summary_field": "summary",
            },
            "judge": {"pass_threshold": 4},
            "prompts": {
                "summarizer_template_path": "prompts/summarizer.jinja2",
                "judge_template_path": "prompts/judge.jinja2",
            },
        }
    )

    mock_dataset = {
        "test": [
            {"id": "1", "dialogue": "Hello world", "summary": "Greeting"},
            {"id": "2", "dialogue": "Goodbye", "summary": "Farewell"},
        ]
    }

    with patch("evals.summarisation.src.runner.load_dataset", return_value=mock_dataset):
        examples = _load_data_pairs(cfg, split="test", limit=None)

    assert len(examples) == 2
    assert examples[0].example_id == "1"
    assert examples[0].dialogue == "Hello world"
    assert examples[0].reference_summary == "Greeting"
    assert examples[1].example_id == "2"


def test_load_data_pairs_with_limit():
    cfg = AppConfig.model_validate(
        {
            "run": {"output_dir": "output"},
            "dataset": {
                "name": "test_dataset",
                "dialogue_field": "dialogue",
                "reference_summary_field": "summary",
            },
            "judge": {"pass_threshold": 4},
            "prompts": {
                "summarizer_template_path": "prompts/summarizer.jinja2",
                "judge_template_path": "prompts/judge.jinja2",
            },
        }
    )

    mock_rows = [
        {"id": "1", "dialogue": "First", "summary": "S1"},
        {"id": "2", "dialogue": "Second", "summary": "S2"},
        {"id": "3", "dialogue": "Third", "summary": "S3"},
    ]
    mock_dataset_split = Mock()
    mock_dataset_split.__iter__ = Mock(return_value=iter(mock_rows))
    mock_dataset_split.select = Mock(return_value=mock_rows[:2])
    mock_dataset_split.__len__ = Mock(return_value=3)

    mock_dataset = {"test": mock_dataset_split}

    with patch("evals.summarisation.src.runner.load_dataset", return_value=mock_dataset):
        examples = _load_data_pairs(cfg, split="test", limit=2)

    mock_dataset_split.select.assert_called_once()
    assert len(examples) == 2


def test_load_data_pairs_missing_id_uses_index():
    cfg = AppConfig.model_validate(
        {
            "run": {"output_dir": "output"},
            "dataset": {
                "name": "test_dataset",
                "dialogue_field": "dialogue",
                "reference_summary_field": "summary",
            },
            "judge": {"pass_threshold": 4},
            "prompts": {
                "summarizer_template_path": "prompts/summarizer.jinja2",
                "judge_template_path": "prompts/judge.jinja2",
            },
        }
    )

    mock_dataset = {
        "test": [
            {"dialogue": "Hello", "summary": "Hi"},
        ]
    }

    with patch("evals.summarisation.src.runner.load_dataset", return_value=mock_dataset):
        examples = _load_data_pairs(cfg, split="test", limit=None)

    assert examples[0].example_id == "0"


def test_to_dspy_devset():
    examples = [
        DialogExample(example_id="1", dialogue="Hello", reference_summary="Hi"),
        DialogExample(example_id="2", dialogue="Bye", reference_summary="Goodbye"),
    ]

    devset = _to_dspy_devset(examples)

    assert len(devset) == 2
    assert isinstance(devset[0], dspy.Example)
    assert devset[0].example_id == "1"
    assert devset[0].dialogue == "Hello"
    assert devset[0].reference_summary == "Hi"
    assert "dialogue" in devset[0].inputs()


def test_run_eval_contract_returns_valid_paths(tmp_path):
    """CONTRACT TEST: run_eval returns valid run_id and Path objects for results."""
    cfg = AppConfig.model_validate(
        {
            "run": {"output_dir": str(tmp_path / "output")},
            "dataset": {
                "name": "test_dataset",
                "dialogue_field": "dialogue",
                "reference_summary_field": "summary",
            },
            "judge": {"pass_threshold": 4},
            "metrics": ["faithfulness"],
            "prompts": {
                "summarizer_template_path": "prompts/summarizer.jinja2",
                "judge_template_path": "prompts/judge.jinja2",
            },
        }
    )

    mock_rows = [{"id": "1", "dialogue": "Test dialogue", "summary": "Test summary"}]
    mock_dataset_split = Mock()
    mock_dataset_split.__iter__ = Mock(return_value=iter(mock_rows))
    mock_dataset_split.select = Mock(return_value=mock_rows)
    mock_dataset_split.__len__ = Mock(return_value=1)
    mock_dataset = {"test": mock_dataset_split}

    mock_llm = MagicMock()
    mock_llm.invoke.return_value = Mock(content="Generated summary")

    mock_metric = MagicMock()
    mock_metric.name = "judge_faithfulness"
    mock_metric.evaluate.return_value = Mock(score=1.0, reason="Good")

    mock_evaluator = MagicMock()
    mock_evaluator.return_value = 0.95

    with (
        patch("evals.summarisation.src.runner.load_dataset", return_value=mock_dataset),
        patch("evals.summarisation.src.runner._build_llm", return_value=mock_llm),
        patch("evals.summarisation.src.runner.build_metrics", return_value=[mock_metric]),
        patch("evals.summarisation.src.runner.get_settings") as mock_settings,
        patch("evals.summarisation.src.runner.Evaluate", return_value=mock_evaluator),
    ):
        mock_settings.return_value.BEST_LLM_MODEL_NAME = "test-model"

        run_id, results_path, summary_path = run_eval(
            cfg,
            split="test",
            limit=1,
            prompt_version="v1",
        )

    assert run_id is not None
    assert isinstance(results_path, Path)
    assert isinstance(summary_path, Path)

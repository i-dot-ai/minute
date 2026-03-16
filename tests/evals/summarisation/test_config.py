from __future__ import annotations

import pytest

from evals.summarisation.src.config import AppConfig, load_config


def test_load_config_parses_yaml(tmp_path):
    output_dir = "test_runs"
    seed = 42
    split = "validation"

    config_path = tmp_path / "config.yaml"
    config_content = f"""
run:
  output_dir: "{output_dir}"
  seed: {seed}
  split: "{split}"
  limit: 10
  prompt_version: "v1"

dataset:
  name: "knkarthick/dialogsum"
  config: null
  dialogue_field: "dialogue"
  reference_summary_field: "summary"

judge:
  pass_threshold: 4

metrics:
  - faithfulness
  - coverage

prompts:
  summarizer_template_path: "prompts/summarizer.jinja2"
  judge_template_path: "prompts/judge.jinja2"
"""
    config_path.write_text(config_content, encoding="utf-8")

    config = load_config(config_path)

    assert config.run.output_dir == output_dir
    assert config.run.seed == seed
    assert config.run.split == split


def test_load_config_parses_yaml_additional_fields(tmp_path):
    limit = 10
    dataset_name = "knkarthick/dialogsum"
    pass_threshold = 4
    metrics = ["faithfulness", "coverage"]

    config_path = tmp_path / "config.yaml"
    config_content = f"""
run:
  output_dir: "test_runs"
  seed: 42
  split: "validation"
  limit: {limit}
  prompt_version: "v1"

dataset:
  name: "{dataset_name}"
  config: null
  dialogue_field: "dialogue"
  reference_summary_field: "summary"

judge:
  pass_threshold: {pass_threshold}

metrics:
  - {metrics[0]}
  - {metrics[1]}

prompts:
  summarizer_template_path: "prompts/summarizer.jinja2"
  judge_template_path: "prompts/judge.jinja2"
"""
    config_path.write_text(config_content, encoding="utf-8")

    config = load_config(config_path)

    assert config.run.limit == limit
    assert config.dataset.name == dataset_name
    assert config.judge.pass_threshold == pass_threshold
    assert config.metrics == metrics


def test_load_config_uses_defaults(tmp_path):
    default_seed = 0
    default_split = "test"

    config_path = tmp_path / "config.yaml"
    config_content = """
run:
  output_dir: "runs"

dataset:
  name: "knkarthick/dialogsum"

judge:
  pass_threshold: 4

prompts:
  summarizer_template_path: "prompts/summarizer.jinja2"
  judge_template_path: "prompts/judge.jinja2"
"""
    config_path.write_text(config_content, encoding="utf-8")

    config = load_config(config_path)

    assert config.run.seed == default_seed
    assert config.run.split == default_split
    assert config.run.limit is None


def test_load_config_uses_defaults_dataset_fields(tmp_path):
    default_dialogue_field = "dialogue"
    default_summary_field = "summary"
    default_metrics_count = 4

    config_path = tmp_path / "config.yaml"
    config_content = """
run:
  output_dir: "runs"

dataset:
  name: "knkarthick/dialogsum"

judge:
  pass_threshold: 4

prompts:
  summarizer_template_path: "prompts/summarizer.jinja2"
  judge_template_path: "prompts/judge.jinja2"
"""
    config_path.write_text(config_content, encoding="utf-8")

    config = load_config(config_path)

    assert config.dataset.dialogue_field == default_dialogue_field
    assert config.dataset.reference_summary_field == default_summary_field
    assert len(config.metrics) == default_metrics_count


def test_app_config_validates_metric_names():
    with pytest.raises(ValueError, match=""):  # noqa: PT011
        AppConfig.model_validate(
            {
                "run": {"output_dir": "runs"},
                "dataset": {"name": "test"},
                "judge": {"pass_threshold": 4},
                "metrics": ["invalid_metric"],
                "prompts": {
                    "summarizer_template_path": "prompts/summarizer.jinja2",
                    "judge_template_path": "prompts/judge.jinja2",
                },
            }
        )

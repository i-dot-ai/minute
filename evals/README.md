# Summarisation Evaluation

Config-driven eval runner for DialogSum-style conversational summarization.

**Important: Run all commands from project root.**

## Setup

```bash
poetry install --with evals-summarisation
```

## Usage

```bash
# Quick smoke test (2 examples)
poetry run python evals/summarisation/src/evaluate.py

# Full test suite
poetry run python evals/summarisation/src/evaluate.py --config evals/summarisation/configs/test.yaml
```

**Available configs:**
- `smoke-test.yaml` - Fast smoke test with `limit: 2`
- `test.yaml` - Full test suite (no limit)

Outputs are written to `evals/summarisation/output/<run_id>/results.jsonl` and `evals/summarisation/output/<run_id>/summary.json`.

## Running a new experiment

An experiment is defined by:

- A config file in `evals/summarisation/configs/` (dataset, model/judge settings, run parameters like split/limit/prompt_version, and which prompt templates to use).
- Prompt templates in `evals/summarisation/prompts/` (how we ask the model to summarise, and how we ask the judge to score).

All run parameters (`split`, `limit`, `prompt_version`) are now configured in the YAML file under the `run:` section, not as CLI flags.

# Transcription Evaluation

Compares transcription services using the AMI Corpus (auto-downloaded to `input/ami/`).

## Setup

```bash
brew install ffmpeg  # macOS
poetry install --with worker,local-dev,evals-transcription
```

## Usage

```bash
# Run default config (smoketest)
poetry run python evals/transcription/src/evaluate.py

# Run specific config
poetry run python evals/transcription/src/evaluate.py --config larger_cloud_test.yaml
```

**Configs:** `evals/transcription/configs/` (`smoketest.yaml`, `larger_cloud_test.yaml`)

**Results:** `evals/transcription/output/`

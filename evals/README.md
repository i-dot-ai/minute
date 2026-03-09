# Summarisation Evaluation

Config-driven eval runner for DialogSum-style conversational summarization.

## Setup

```bash
poetry install --with evals-summarisation
```

## Usage

```bash
# Run default config
poetry run python evals/summarisation/src/evaluate.py --config evals/summarisation/configs/default.yaml --split test --limit 50
```

Outputs are written to `evals/summarisation/output/<run_id>/results.jsonl` and `evals/summarisation/output/<run_id>/summary.json`.

## Running a new experiment

An experiment is defined by:

- A config file in `evals/summarisation/configs/` (dataset, model/judge settings, and which prompt templates to use).
- Prompt templates in `evals/summarisation/prompts/` (how we ask the model to summarise, and how we ask the judge to score).

Update the config file and/or prompt templates as needed, then run the experiment.

# Transcription Evaluation

Compares transcription services using the AMI Corpus (auto-downloaded to `input/).

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

Configs in `evals/transcription/configs/`: `smoketest.yaml`, `larger_cloud_test.yaml`

Results → `evals/transcription/output/`

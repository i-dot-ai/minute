# Transcription Evaluation Suite

Evaluation framework for comparing transcription services using the AMI Corpus dataset.

## Setup

Requires FFmpeg for audio processing. Install from project root:

```bash
brew install ffmpeg  # macOS
poetry install --with worker,local-dev,evals
```

## Usage

**CLI Arguments**:
- `--num-samples N`: Evaluate N meetings (default: all available)
- `--sample-duration-fraction 0.X`: Use first X% of each meeting (e.g., `0.1` = 10%)
- `--max-workers N`: Parallel workers (default: 4, use `1` for local adapters like Whisper)
- `--prepare-only`: Cache dataset without transcription

**Example** - Quick smoke test with 2 meetings at 10% duration:
```bash
poetry run python evals/transcription/src/evaluate.py \
  --num-samples 2 \
  --sample-duration-fraction 0.1 \
  --max-workers 1
```

Results saved to `evals/transcription/results/evaluation_results_YYYYMMDD_HHMMSS.json`.

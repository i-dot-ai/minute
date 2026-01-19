# Transcription Evaluation Suite

Evaluation framework for comparing transcription services.

## System Requirements

### FFmpeg
This project requires FFmpeg for audio processing:

```bash
# macOS
brew install ffmpeg

# Ubuntu/Debian
sudo apt-get update
sudo apt-get install ffmpeg

# Windows
# Download from https://ffmpeg.org/download.html
```

## Setup

1. Install dependencies:
```bash
uv sync
```

2. Configure environment variables:
```bash
cp .env.example .env
# Edit .env with your Azure Speech API credentials
```

## Environment Variables

- `AZURE_SPEECH_KEY`: Your Azure Cognitive Services Speech API key
- `AZURE_SPEECH_REGION`: Your Azure region (e.g., `uksouth`, `eastus`)

## Usage

Run the evaluation:
```bash
uv run python src/evaluate.py --num-samples 10
```

Results are saved to `results/evaluation_results.json` with summaries and per-sample details for both Azure and Whisper.

## Configuration

**Sample Selection**: Use `--num-samples` CLI argument to control how many samples to evaluate. Selects the longest audio clips for faster testing. This is optional - remove the sample selection logic in `src/evaluate.py` for full dataset evaluation.

**Dataset**: Currently uses **LibriSpeech ASR** (generic English speech). To replace: edit `src/core/dataset.py` constants (`DATASET_NAME`, `DATASET_CONFIG`, `DATASET_SPLIT`). 

**Dataset Contract**: Each row must provide:
- `audio["array"]`: 1D numpy array of audio samples (mono)
- `audio["sampling_rate"]`: integer sample rate (e.g., 16000, 44100)
- `text`: string with ground truth transcription

These fields are required for audio processing (resampling, format conversion) and WER computation.

**Adapters**: Modify `src/evaluate.py` to change Whisper model size or Azure language settings.

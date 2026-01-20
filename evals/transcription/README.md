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

**Sample Selection**: Use `--num-samples` CLI argument to control how many meetings to evaluate from the AMI dataset. Each meeting consists of all utterances from all speakers combined into a single chronological audio track.

**Dataset**: Currently uses **AMI Corpus** (meeting recordings with speaker diarization potential). The dataset is streamed and processed on-demand with automatic caching. All utterances per meeting are:
- Sorted chronologically by begin_time
- **Mixed into a timeline-based audio track** using begin_time and end_time timestamps
- Overlapping speech is properly mixed (speakers can talk simultaneously)
- Gaps and silences are preserved based on actual timing
- Transcripts merged with spaces between utterances
- Saved as one processed WAV file per meeting
- Audio is normalized if clipping occurs from overlaps

This creates realistic full-meeting audio for transcription evaluation (typically 80-90 minutes per meeting) that accurately represents the original meeting dynamics including overlapping speech. 

**Dataset Contract**: Each sample provides:
- `audio["array"]`: 1D numpy array of audio samples (mono)
- `audio["sampling_rate"]`: integer sample rate (16000 Hz after processing)
- `audio["path"]`: path to cached processed audio file
- `text`: string with ground truth transcription
- `meeting_id`: unique identifier for the meeting
- `duration_sec`: duration of the audio in seconds

The AMI dataset loader automatically handles:
- Downloading raw audio from the dataset
- Converting to mono 16kHz PCM WAV format
- Caching processed files in `cache/processed/`
- Cleaning up raw files after processing
- Reusing cached files on subsequent runs

**Adapters**: Modify `src/evaluate.py` to change Whisper model size or Azure language settings.

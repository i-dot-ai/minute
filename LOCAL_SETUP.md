# Local Setup Guide

Run Minute locally with hardware-accelerated transcription and local Ollama LLM.

## Prerequisites

**System Requirements:**
- Docker Desktop (required for any local setup)
- Python 3.12 (required for any local setup)
- Poetry (required for any local setup)
- FFmpeg
- Ollama

**macOS Installation:**
```bash
brew install ffmpeg poetry
```
Afterwards install Ollama from: https://ollama.com/download/mac


**Required:**
1. **HuggingFace Token**: https://huggingface.co/settings/tokens (starts with `hf_`)
   - Accept terms at: https://huggingface.co/pyannote/segmentation-3.0
   - Accept terms at: https://huggingface.co/pyannote/speaker-diarization-3.1
   - **Note**: The organization question while accepting terms is unimportant, as we are using these models for quick local tests only without distillation/training etc. Don't hesitate to put 'N/A' there.

## Quick Start

```bash
# Install dependencies
poetry install --with worker,local-dev

# Download Ollama model
ollama pull llama3.2:3b-instruct-q4_K_M

# Configure environment
cp .env.local .env
```
Before moving on to the next step, edit the .env file and add: WHISPLY_HF_TOKEN=hf_your_token
```bash
# Run worker locally
./run-worker-local.sh
```

### Access the app at http://localhost:3000

> **Note**: The first transcription will take significantly longer as it downloads 2 annotation models and 1 transcription model (3 large files). These files are cached locally and only need to be downloaded once.

**Troubleshooting Ollama:**

If you encounter this error:
```
ollama pull llama3.2:3b-instruct-q4_K_M
Error: ollama server not responding - could not find ollama app
```

You need to launch the Ollama GUI application. Search for 'ollama' in your applications and open it.

## Architecture

- **Docker**: Database, backend, frontend, localstack
- **Local Worker**: Runs natively for GPU access (MPS on Apple Silicon)
- **Transcription**: Whisply with hardware acceleration
- **LLM**: Ollama (local, runs natively for MPS acceleration)

## Troubleshooting Docker

The local dev implementation of Minute doesn't impact Docker services except that the worker runs directly on hardware instead of through Docker.

If you encounter Docker issues, the fastest solution is to reset Docker completely:

**⚠️ Warning**: This command will delete all built images, volumes, and database data. Back up any data you want to preserve.

```bash
docker compose down -v
```

## API Portal

To gain & validate access to the platform

-  Install the Azure CLI if needed
-  Login with the command below, when prompted, provide  with your test account credentials
```
az login --scope api://api.azc.test.communities.gov.uk/.default

```
- Get your access token via the command below and set it to the AZURE_APIM_ACCESS_TOKEN key within your env file
```
az account get-access-token

```
- Finally, run the 'test-apim.py' script within root. On success, you should receive the following response 

```
message=ChatCompletionMessage(content="Hello, APIM Test Team! 👋 Hope you're all doing great and having a productive day. Let me know how I can assist you! 🚀" ...)

```

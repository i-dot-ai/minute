#!/bin/bash

# rehydrate google account credentials
mkdir -p /app/config/
echo $GOOGLE_APPLICATION_CREDENTIALS_BASE64 | base64 -d > /app/config/google-credentials.json
export GOOGLE_APPLICATION_CREDENTIALS=/app/config/google-credentials.json

# Main execution
echo "Starting Temporal worker..."

# Run the venv interpreter directly (it is first on PATH from the Dockerfile)
# rather than via `uv run`, which could re-sync/mutate /app/.venv while the process is live.
exec python worker/temporal_worker.py
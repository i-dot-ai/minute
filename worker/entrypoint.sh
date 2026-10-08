#!/bin/bash

# rehydrate google account credentials
mkdir -p /app/config/
echo $GOOGLE_APPLICATION_CREDENTIALS_BASE64 | base64 -d > /app/config/google-credentials.json
export GOOGLE_APPLICATION_CREDENTIALS=/app/config/google-credentials.json

# Main execution
echo "Starting worker..."

# Run the venv interpreter directly (it is first on PATH from the Dockerfile)
# rather than via `uv run`, so uv can never re-sync/mutate /app/.venv at runtime.
exec python worker/main.py
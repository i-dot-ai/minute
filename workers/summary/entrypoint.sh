#!/bin/bash

# Summary (LLM) worker: generates minutes/edits and interactive chat via Gemini,
# so it needs Google credentials rehydrated.
mkdir -p /app/config/
echo $GOOGLE_APPLICATION_CREDENTIALS_BASE64 | base64 -d > /app/config/google-credentials.json
export GOOGLE_APPLICATION_CREDENTIALS=/app/config/google-credentials.json

echo "Starting summary worker..."

# Run the venv interpreter directly (it is first on PATH from the Dockerfile)
# rather than via `uv run`. This guarantees uv can never re-sync/mutate /app/.venv
# while the worker process is live. Run as a module so /app is the import root.
exec python -m workers.summary.main

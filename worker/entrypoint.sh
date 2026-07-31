#!/bin/bash

# rehydrate google account credentials
mkdir -p /app/config/
echo $GOOGLE_APPLICATION_CREDENTIALS_BASE64 | base64 -d > /app/config/google-credentials.json
export GOOGLE_APPLICATION_CREDENTIALS=/app/config/google-credentials.json

# Main execution
echo "Starting queue service..."

# Run the venv interpreter directly (it is first on PATH from the Dockerfile)
# rather than via `uv run`. Ray starts a local cluster here and spawns many
# long-lived subprocesses off sys.executable; keeping uv out of the runtime path
# guarantees it can never re-sync/mutate /app/.venv while those processes are live.
exec python worker/main.py
#!/bin/bash

# rehydrate google account credentials
mkdir -p /app/config/
echo $GOOGLE_APPLICATION_CREDENTIALS_BASE64 | base64 -d > /app/config/google-credentials.json
export GOOGLE_APPLICATION_CREDENTIALS=/app/config/google-credentials.json

# Main execution
echo "Starting queue service..."

poetry run uvicorn worker.healthcheck:app --host 0.0.0.0 --port 8080 &

exec poetry run python worker/main.py
#!/bin/bash

# rehydrate google account credentials (kept for parity with the other services in
# case a storage/transcription path needs them; harmless if the env var is unset)
mkdir -p /app/config/
echo $GOOGLE_APPLICATION_CREDENTIALS_BASE64 | base64 -d > /app/config/google-credentials.json
export GOOGLE_APPLICATION_CREDENTIALS=/app/config/google-credentials.json

echo "Starting audio worker..."

exec python audio_worker/main.py

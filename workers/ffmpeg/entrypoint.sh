#!/bin/bash

# FFmpeg worker: audio preprocessing only. It does no LLM/transcription API calls,
# so it does not need Google credentials rehydrated.
echo "Starting ffmpeg worker..."

# Run the venv interpreter directly (it is first on PATH from the Dockerfile)
# rather than via `uv run`. This guarantees uv can never re-sync/mutate /app/.venv
# while the worker process is live.
#
# Run as a module (`-m workers.ffmpeg.main`) rather than by path. Executing the
# script by path puts /app/workers at sys.path[0], which makes `import ffmpeg`
# resolve to the local workers/ffmpeg package instead of the installed
# ffmpeg-python package. Running with -m keeps /app as the import root.
exec python -m workers.ffmpeg.main

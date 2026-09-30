FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1

# uv configuration: install into a project virtualenv at a known path and put it on PATH
ENV UV_PROJECT_ENVIRONMENT=/app/.venv
ENV UV_COMPILE_BYTECODE=1
ENV UV_LINK_MODE=copy
ENV UV_NO_SYNC=1
ENV PATH="/app/.venv/bin:$PATH"

# Install system dependencies (ffmpeg lives here now, not in the Ray worker)
RUN apt-get update && apt-get install -y ffmpeg curl && rm -rf /var/lib/apt/lists/*

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

# Copy only dependency manifests to cache them in a docker layer
COPY pyproject.toml uv.lock README.md ./

# Install project dependencies (without the project itself) for the audio worker
RUN uv sync --frozen --no-install-project --no-group dev

# Copy the application code
COPY common common
COPY backend/__init__.py backend/__init__.py
COPY audio_worker audio_worker

# Install the project itself now that the source is present
RUN uv sync --frozen --no-default-groups --group audio-worker

RUN chmod +x audio_worker/entrypoint.sh

CMD [ "audio_worker/entrypoint.sh" ]

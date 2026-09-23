FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1

# uv configuration: install into a project virtualenv at a known path and put it on PATH
ENV UV_PROJECT_ENVIRONMENT=/app/.venv
ENV UV_COMPILE_BYTECODE=1
ENV UV_LINK_MODE=copy
ENV UV_NO_SYNC=1
ENV PATH="/app/.venv/bin:$PATH"

# Install system dependencies. The LLM worker does no audio processing, so ffmpeg
# is intentionally NOT installed here (curl is kept for diagnostics).
RUN apt-get update && apt-get install -y --no-install-recommends curl && rm -rf /var/lib/apt/lists/*

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

# Copy only dependency manifests to cache them in a docker layer
COPY pyproject.toml uv.lock README.md ./

# Install only this worker's dependencies (without the project itself)
RUN uv sync --frozen --no-install-project --no-default-groups --group worker-summary

# Copy the application code
COPY common common
COPY backend/__init__.py backend/__init__.py
COPY workers workers

# Install the project itself now that the source is present
RUN uv sync --frozen --no-default-groups --group worker-summary

RUN chmod +x workers/summary/entrypoint.sh

CMD [ "workers/summary/entrypoint.sh" ]

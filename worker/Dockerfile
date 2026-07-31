FROM python:3.12-slim

# The following three ENVs are to ensure ray logs appear properly
ENV RAY_ROTATION_MAX_BYTES=10485760
ENV RAY_ROTATION_BACKUP_COUNT=1
ENV PYTHONUNBUFFERED=1

# uv configuration: install into a project virtualenv at a known path and put it on PATH
ENV UV_PROJECT_ENVIRONMENT=/app/.venv
ENV UV_COMPILE_BYTECODE=1
ENV UV_LINK_MODE=copy
ENV UV_NO_SYNC=1
ENV PATH="/app/.venv/bin:$PATH"

# Install system dependencies
RUN apt-get update && apt-get install -y ffmpeg curl && rm -rf /var/lib/apt/lists/*

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

# Copy only dependency manifests to cache them in a docker layer
COPY pyproject.toml uv.lock README.md ./

# Install project dependencies (without the project itself) for the worker
RUN uv sync --frozen --no-install-project --no-group dev 

# Copy the FastAPI application code
COPY common common
COPY backend/__init__.py backend/__init__.py
COPY worker worker

# Install the project itself now that the source is present
RUN uv sync --frozen --no-default-groups --group worker

RUN chmod +x worker/entrypoint.sh

CMD [ "worker/entrypoint.sh" ]

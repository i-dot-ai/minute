# ==========================================
# Stage 1: Builder
# ==========================================
FROM python:3.12-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Install system dependencies and Poetry
RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*
RUN pip install --no-cache-dir poetry

WORKDIR /app

# Tell Poetry to create the virtualenv inside the project directory (/app/.venv)
ENV POETRY_VIRTUALENVS_IN_PROJECT=true

# Copy dependency files first
COPY pyproject.toml poetry.lock README.md ./
RUN poetry install --with worker --without dev --no-interaction --no-ansi --no-root

# Copy application code
COPY common common
COPY backend/__init__.py backend/__init__.py
COPY worker worker

# Install again to include the root project
RUN poetry install --with worker --without dev --no-interaction --no-ansi


# ==========================================
# Stage 2: Runner
# ==========================================
FROM python:3.12-slim

ENV RAY_ROTATION_MAX_BYTES=10485760
ENV RAY_ROTATION_BACKUP_COUNT=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Install ffmpeg in the runner
RUN apt-get update && apt-get install -y ffmpeg && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy the fully built virtual environment from the builder
COPY --from=builder /app/.venv /app/.venv
# Put the virtual environment on the path
ENV PATH="/app/.venv/bin:$PATH"

# Copy the application code
COPY common common
COPY backend/__init__.py backend/__init__.py
COPY worker worker

RUN chmod +x worker/entrypoint.sh

CMD ["worker/entrypoint.sh"]
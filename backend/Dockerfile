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

# Copy only dependency files first (for Docker layer caching)
COPY pyproject.toml poetry.lock README.md ./
RUN poetry install --with backend --without dev --no-interaction --no-ansi --no-root

# Copy application code
COPY backend backend
COPY common common
COPY worker/__init__.py worker/__init__.py
COPY alembic alembic
COPY alembic.ini alembic.ini

# Install again to include the root project and path dependencies
RUN poetry install --with backend --without dev --no-interaction --no-ansi


# ==========================================
# Stage 2: Runner
# ==========================================
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Copy the completely built virtual environment from the builder
COPY --from=builder /app/.venv /app/.venv
# Put the virtual environment on the path
ENV PATH="/app/.venv/bin:$PATH"

# Copy the application code
COPY backend backend
COPY common common
COPY worker/__init__.py worker/__init__.py
COPY alembic alembic
COPY alembic.ini alembic.ini

RUN chmod +x backend/entrypoint.sh

EXPOSE 8080
ENTRYPOINT ["backend/entrypoint.sh"]
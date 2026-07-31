FROM python:3.12-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# uv configuration: install into a project virtualenv at a known path and put it on PATH
ENV UV_PROJECT_ENVIRONMENT=/app/.venv
ENV UV_COMPILE_BYTECODE=1
ENV UV_LINK_MODE=copy
ENV UV_NO_SYNC=1
ENV PATH="/app/.venv/bin:$PATH"

# Install system dependencies
RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Set the working directory
WORKDIR /app

# Copy only dependency manifests to cache them in a docker layer
COPY pyproject.toml uv.lock README.md ./

# Install project dependencies (without the project itself).
RUN uv sync --frozen --no-install-project --no-group dev

# Copy the FastAPI application code
COPY backend backend
COPY common common
COPY worker/__init__.py worker/__init__.py
COPY alembic alembic
COPY alembic.ini alembic.ini
# Expose the port the app runs on
EXPOSE 8080
RUN chmod +x backend/entrypoint.sh

# Command to run the FastAPI app using Uvicorn
ENTRYPOINT ["backend/entrypoint.sh"]

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
RUN apt-get update && apt-get install -y --no-install-recommends curl && rm -rf /var/lib/apt/lists/*

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Set the working directory
WORKDIR /app

# Copy only dependency manifests to cache them in a docker layer
COPY pyproject.toml uv.lock README.md ./

# Install only the backend's dependencies (without the project itself). Using
# --no-default-groups + --group backend keeps the worker-only SDKs (google-genai,
# ffmpeg-python, azure-storage-blob) out of the API image.
RUN uv sync --frozen --no-install-project --no-default-groups --group backend

# Copy the FastAPI application code
COPY backend backend
COPY common common
COPY workers/__init__.py workers/__init__.py
COPY alembic alembic
COPY alembic.ini alembic.ini
# Expose the port the app runs on
EXPOSE 8080
RUN chmod +x backend/entrypoint.sh

# Command to run the FastAPI app using Uvicorn
ENTRYPOINT ["backend/entrypoint.sh"]

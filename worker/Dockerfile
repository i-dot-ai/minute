FROM python:3.12-slim

# The following three ENVs are to ensure ray logs appear properly
ENV RAY_ROTATION_MAX_BYTES=10485760
ENV RAY_ROTATION_BACKUP_COUNT=1
ENV PYTHONUNBUFFERED=1

# Install system dependencies and Poetry
RUN apt-get update && apt-get install -y ffmpeg
RUN pip install --no-cache-dir poetry

WORKDIR /app

# Copy only requirements to cache them in docker layer
COPY pyproject.toml poetry.lock README.md ./

# Configure poetry
RUN poetry config virtualenvs.create false

# Install project dependencies
RUN poetry install --with worker --without dev --no-interaction --no-ansi --no-root

# Copy the FastAPI application code
COPY common common
COPY backend backend
COPY worker worker

RUN poetry install --only-root

RUN chmod +x worker/entrypoint.sh

CMD [ "worker/entrypoint.sh" ]

FROM python:3.12-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Install system dependencies and Poetry
RUN apt-get update && apt-get install -y \
    gcc \
    python3-dev \
    build-essential \
    curl \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/* \
    && pip install --no-cache-dir poetry

# Set the working directory
WORKDIR /app

RUN cat <<EOF > ./health.sh
curl --fail http://localhost:8080/healthcheck
EOF
RUN chmod +x ./health.sh

# Copy only requirements to cache them in docker layer
COPY pyproject.toml poetry.lock README.md ./

# Configure poetry
RUN poetry config virtualenvs.create false

# Install project dependencies
RUN poetry install --with backend --without dev --no-interaction --no-ansi --no-root

# Copy the FastAPI application code
COPY backend backend
COPY common common
COPY alembic alembic
COPY alembic.ini alembic.ini
# Expose the port the app runs on
EXPOSE 8080
RUN chmod +x backend/entrypoint.sh

# Command to run the FastAPI app using Uvicorn
ENTRYPOINT ["backend/entrypoint.sh"]

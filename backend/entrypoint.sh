#!/bin/bash

# Function to run database migrations
run_migrations() {
    echo "Running database migrations..."
    poetry run alembic upgrade head
    if [ $? -ne 0 ]; then
        echo "Database migration failed!"
        exit 1
    fi
    echo "Database migrations completed successfully"
}

# Function to start the FastAPI application
start_app() {
    echo "Starting FastAPI application..."
    poetry run uvicorn backend.main:app --host 0.0.0.0 --port 8080 &
    PID=$!
    wait $PID
}

# rehydrate google account credentials
mkdir -p /app/config/
echo $GOOGLE_APPLICATION_CREDENTIALS_BASE64 | base64 -d > /app/config/google-credentials.json
export GOOGLE_APPLICATION_CREDENTIALS=/app/config/google-credentials.json

# Main execution
run_migrations
start_app
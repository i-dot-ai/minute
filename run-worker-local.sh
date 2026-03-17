#!/bin/bash

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/setup-ollama.sh"

cleanup() {
    echo ""
    echo "Shutting down worker..."
    cleanup_ollama
    exit 0
}

trap cleanup SIGINT SIGTERM

echo "Starting Minute Worker with MPS Acceleration"
echo ""

if [ ! -f .env ]; then
    echo "Creating .env from .env.local..."
    cp .env.local .env
    echo "IMPORTANT: Edit .env and set WHISPLY_HF_TOKEN"
    echo "Get token from: https://huggingface.co/settings/tokens"
    echo ""
    read -p "Press Enter after adding your HuggingFace token to .env..."
fi

echo "Checks:"
echo -n "[1/5] MPS availability... "
MPS_AVAILABLE=$(poetry run python -c "import torch; print(torch.backends.mps.is_available())" 2>/dev/null || echo "false")
if [ "$MPS_AVAILABLE" = "True" ]; then
    echo "✓"
else
    echo "✗ (will use CPU)"
fi

echo ""
echo "[2/5] Ollama Setup:"
setup_ollama || exit 1

echo ""
echo "[3/5] Docker Desktop:"
echo -n "  Checking Docker... "
if ! docker info > /dev/null 2>&1; then
    echo "✗ (not running)"
    echo "  Starting Docker Desktop..."
    open -a Docker
    echo -n "  Waiting for Docker... "
    max_wait=60
    waited=0
    while ! docker info > /dev/null 2>&1 && [ $waited -lt $max_wait ]; do
        sleep 2
        waited=$((waited + 2))
    done
    if ! docker info > /dev/null 2>&1; then
        echo "✗"
        echo "  ERROR: Docker failed to start. Please start Docker Desktop manually."
        exit 1
    fi
    echo "✓"
else
    echo "✓"
fi

echo -n "  Starting services... "
docker compose stop worker 2>/dev/null || true
docker compose up -d db localstack backend frontend > /dev/null 2>&1
echo "✓"

wait_for_service() {
    local service_name=$1
    local check_command=$2
    local log_service=$3
    local max_retries=30
    local retry_count=0
    
    while [ $retry_count -lt $max_retries ]; do
        if eval "$check_command" > /dev/null 2>&1; then
            return 0
        fi
        retry_count=$((retry_count + 1))
        sleep 2
    done
    
    echo ""
    echo "  ERROR: $service_name failed. Check: docker compose logs $log_service"
    exit 1
}

echo ""
echo "[4/5] Service Health Checks:"
echo -n "  Database... "
wait_for_service "Database" "docker compose ps db | grep -q 'healthy'" "db"
echo "✓"
echo -n "  Backend... "
wait_for_service "Backend" "curl -s http://localhost:8080/healthcheck" "backend"
echo "✓"
echo -n "  Frontend... "
wait_for_service "Frontend" "curl -s http://localhost:3000" "frontend"
echo "✓"

echo ""
echo "Rest of the App is Ready:"
echo "  Application: http://localhost:3000"
echo ""
echo "Starting worker (Ctrl+C to stop)..."
echo ""

exec poetry run python worker/main.py

#!/bin/bash

set -e

OLLAMA_PID=""

cleanup_ollama() {
    if [ ! -z "$OLLAMA_PID" ]; then
        echo "Shutting down Ollama..."
        kill $OLLAMA_PID 2>/dev/null || true
    fi
}

setup_ollama() {
    echo -n "  Ollama installed... "
    if ! command -v ollama &> /dev/null; then
        echo "✗"
        echo "  ERROR: Install Ollama: brew install ollama"
        return 1
    fi
    echo "✓"

    echo -n "  Ollama service... "
    if ! pgrep -x "ollama" > /dev/null; then
        ollama serve > /tmp/ollama.log 2>&1 &
        OLLAMA_PID=$!
        sleep 3
    fi
    if ! curl -s http://localhost:11434/api/tags > /dev/null 2>&1; then
        echo "✗"
        echo "  ERROR: Ollama not responding. Check /tmp/ollama.log"
        return 1
    fi
    echo "✓"

    echo -n "  Ollama models... "
    FAST_MODEL=$(grep "FAST_LLM_MODEL_NAME" .env 2>/dev/null | cut -d'=' -f2 || echo "llama3.2:3b-instruct-q4_K_M")
    BEST_MODEL=$(grep "BEST_LLM_MODEL_NAME" .env 2>/dev/null | cut -d'=' -f2 || echo "llama3.2:3b-instruct-q4_K_M")
    for MODEL in "$FAST_MODEL" "$BEST_MODEL"; do
        if [ -n "$MODEL" ] && ! ollama list | grep -q "$MODEL"; then
            echo "✗"
            echo "  ERROR: Model '$MODEL' not found. Run: ollama pull $MODEL"
            return 1
        fi
    done
    echo "✓"
    
    return 0
}

if [ "${BASH_SOURCE[0]}" = "${0}" ]; then
    trap cleanup_ollama SIGINT SIGTERM EXIT
    
    echo "Setting up Ollama..."
    echo ""
    
    if setup_ollama; then
        echo ""
        echo "Ollama is ready at http://localhost:11434"
        echo "Press Ctrl+C to stop"
        echo ""
        
        if [ ! -z "$OLLAMA_PID" ]; then
            wait $OLLAMA_PID
        else
            while true; do
                sleep 3600
            done
        fi
    else
        exit 1
    fi
fi

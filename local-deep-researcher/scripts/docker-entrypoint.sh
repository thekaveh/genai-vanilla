#!/bin/bash
set -e

REPO_URL="https://github.com/langchain-ai/local-deep-researcher.git"
REPO_DIR="/app/repo"

echo "Local Deep Researcher: Starting initialization..."

# -------------------------------------------------------------------
# Fetch latest upstream code (clone on first run, pull on restart)
# -------------------------------------------------------------------
echo "Local Deep Researcher: Syncing upstream repository..."
if [ -d "$REPO_DIR/.git" ]; then
    echo "Local Deep Researcher: Pulling latest changes..."
    if git -C "$REPO_DIR" pull --ff-only 2>/dev/null; then
        echo "Local Deep Researcher: Repository updated successfully"
    else
        echo "Local Deep Researcher: Pull failed — re-cloning..."
        rm -rf "$REPO_DIR"/.* "$REPO_DIR"/* 2>/dev/null || true
        git clone "$REPO_URL" "$REPO_DIR"
    fi
else
    echo "Local Deep Researcher: Cloning repository..."
    rm -rf "$REPO_DIR"/.* "$REPO_DIR"/* 2>/dev/null || true
    git clone "$REPO_URL" "$REPO_DIR"
fi

# Copy upstream source into working directory (preserving our custom scripts/config)
cp -r "$REPO_DIR"/src /app/
cp "$REPO_DIR"/pyproject.toml /app/
cp "$REPO_DIR"/langgraph.json /app/

echo "Local Deep Researcher: Installing dependencies..."
uv pip install --system -r /app/pyproject.toml

# -------------------------------------------------------------------
# Initialize configuration from database
# -------------------------------------------------------------------
echo "Local Deep Researcher: Initializing configuration from database..."
if ! python3 /app/scripts/init-config.py; then
    echo "Local Deep Researcher: ERROR - Failed to initialize configuration"
    echo "Local Deep Researcher: Check database connectivity and dependencies"
    exit 1
fi

# Wait for Ollama to be available
echo "Local Deep Researcher: Checking Ollama availability..."
if [ ! -f /app/.env ]; then
    echo "Local Deep Researcher: ERROR - Configuration file /app/.env not found"
    exit 1
fi

OLLAMA_URL=$(grep OLLAMA_BASE_URL /app/.env | cut -d'=' -f2)
if [ -z "$OLLAMA_URL" ]; then
    echo "Local Deep Researcher: ERROR - OLLAMA_BASE_URL not found in configuration"
    exit 1
fi
echo "Local Deep Researcher: Using Ollama at: $OLLAMA_URL"

# Wait for Ollama API
max_retries=30
retry_count=0
until curl -s --fail "$OLLAMA_URL/" > /dev/null 2>&1; do
    retry_count=$((retry_count + 1))
    if [ $retry_count -ge $max_retries ]; then
        echo "Local Deep Researcher: ERROR - Ollama API not available after $max_retries attempts"
        exit 1
    fi
    echo "Local Deep Researcher: Waiting for Ollama API (attempt $retry_count/$max_retries)..."
    sleep 5
done

echo "Local Deep Researcher: Ollama API is available"

# Start the LangGraph server
echo "Local Deep Researcher: Starting LangGraph development server..."
cd /app

# Verify required files exist
if [ ! -f "/app/pyproject.toml" ]; then
    echo "Local Deep Researcher: ERROR - pyproject.toml not found"
    exit 1
fi

# Use the langgraph dev command to start the server
echo "Local Deep Researcher: Executing langgraph dev command..."
exec uvx --refresh --from "langgraph-cli[inmem]" --with-editable . --python 3.11 langgraph dev --host 0.0.0.0 --port 2024 --no-reload

#!/bin/sh
set -e

echo "weaviate: Reading dynamic configuration..."

# Check if shared config exists
if [ ! -f "/shared/weaviate-config.env" ]; then
  echo "weaviate: Warning - No dynamic configuration found, using defaults"
  export WEAVIATE_OLLAMA_EMBEDDING_MODEL="nomic-embed-text"
else
  # Source the dynamic configuration
  echo "weaviate: Loading dynamic configuration from weaviate-init"
  . /shared/weaviate-config.env
  echo "weaviate: Using Ollama embedding model: $WEAVIATE_OLLAMA_EMBEDDING_MODEL"
fi

# Export for Weaviate environment
export OLLAMA_DEFAULT_MODEL="$WEAVIATE_OLLAMA_EMBEDDING_MODEL"

# Set default Ollama endpoint for text2vec-ollama module
# This ensures the module uses the correct endpoint based on SOURCE configuration
if [ -n "$OLLAMA_ENDPOINT" ]; then
  export DEFAULT_OLLAMA_API_ENDPOINT="$OLLAMA_ENDPOINT"
  echo "weaviate: Using Ollama endpoint: $OLLAMA_ENDPOINT"
else
  export DEFAULT_OLLAMA_API_ENDPOINT="http://localhost:11434"
  echo "weaviate: Using default Ollama endpoint: http://localhost:11434"
fi

echo "weaviate: Configuration applied - Ollama model: $OLLAMA_DEFAULT_MODEL, endpoint: $DEFAULT_OLLAMA_API_ENDPOINT"

# Execute the original Weaviate command with dynamic configuration
exec "$@"
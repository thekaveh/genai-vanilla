#!/bin/sh
set -e

echo "backend: Reading dynamic Weaviate configuration..."

# Check if shared config exists
if [ -f "/shared/weaviate-config.env" ]; then
  echo "backend: Loading dynamic Weaviate configuration"
  . /shared/weaviate-config.env
  export WEAVIATE_OLLAMA_EMBEDDING_MODEL="$WEAVIATE_OLLAMA_EMBEDDING_MODEL"
  echo "backend: Using Ollama embedding model: $WEAVIATE_OLLAMA_EMBEDDING_MODEL"
else
  echo "backend: Warning - No dynamic Weaviate configuration found"
  export WEAVIATE_OLLAMA_EMBEDDING_MODEL="nomic-embed-text"
  echo "backend: Using default Ollama embedding model: $WEAVIATE_OLLAMA_EMBEDDING_MODEL"
fi

echo "backend: Configuration applied - starting backend service..."

# Execute the original backend command
exec "$@"
#!/bin/sh
set -e

echo "weaviate: Reading dynamic configuration..."

# Check if shared config exists
if [ ! -f "/shared/weaviate-config.env" ]; then
  echo "weaviate: Warning - No dynamic configuration found, using defaults"
  export LITELLM_EMBEDDING_MODEL="ollama/nomic-embed-text"
else
  # Source the dynamic configuration
  echo "weaviate: Loading dynamic configuration from weaviate-init"
  . /shared/weaviate-config.env
  echo "weaviate: Using LiteLLM embedding model: $LITELLM_EMBEDDING_MODEL"
fi

# Weaviate's text2vec-openai module reads its base URL from per-collection
# moduleConfig (set by consumers when creating collections). The API key
# is delivered via Weaviate's OPENAI_APIKEY env, populated from
# LITELLM_MASTER_KEY in docker-compose.yml.

if [ -n "$LITELLM_BASE_URL" ]; then
  export DEFAULT_OPENAI_BASE_URL="$LITELLM_BASE_URL/v1"
  echo "weaviate: Using LiteLLM endpoint: $LITELLM_BASE_URL"
else
  export DEFAULT_OPENAI_BASE_URL="http://litellm:4000/v1"
  echo "weaviate: Using default LiteLLM endpoint: http://litellm:4000"
fi

echo "weaviate: Configuration applied - embedding model: $LITELLM_EMBEDDING_MODEL, base URL: $DEFAULT_OPENAI_BASE_URL"

# Execute the original Weaviate command with dynamic configuration
exec "$@"

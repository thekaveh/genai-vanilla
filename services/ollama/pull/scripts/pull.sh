#!/bin/sh
set -e

echo "ollama-pull: Starting model pull process..."

# Check required env vars
if [ -z "$PGHOST" ] || [ -z "$PGUSER" ] || [ -z "$PGPASSWORD" ] || [ -z "$PGDATABASE" ] || [ -z "$OLLAMA_HOST_URL" ]; then
  echo "ollama-pull: Error: One or more required environment variables are not set."
  echo "PGHOST=$PGHOST, PGUSER=$PGUSER, PGPASSWORD=[set], PGDATABASE=$PGDATABASE, OLLAMA_HOST_URL=$OLLAMA_HOST_URL"
  exit 1
fi

echo "ollama-pull: Installing required tools..."
apk add --no-cache curl postgresql-client

echo "ollama-pull: Waiting for Ollama API at $OLLAMA_HOST_URL..."
sleep 5 # Initial wait
# Bounded wait (300s, mirroring weaviate/minio/n8n init): ollama has no
# compose healthcheck and comfyui-init gates on this container completing,
# so an unbounded loop here used to wedge the whole init chain forever.
WAITED=0
until curl -sf --max-time 5 "$OLLAMA_HOST_URL/" > /dev/null; do
  WAITED=$((WAITED + 5))
  if [ "$WAITED" -ge 300 ]; then
    echo "ollama-pull: ERROR - Ollama API not reachable after 300s; giving up." >&2
    exit 1
  fi
  echo "ollama-pull: Waiting for Ollama API... (${WAITED}s)"
  sleep 5
done
echo "ollama-pull: Ollama API is available."

echo "ollama-pull: Fetching active Ollama models from database $PGDATABASE on $PGHOST..."
psql_output=$(PGPASSWORD="$PGPASSWORD" psql -h "$PGHOST" -p "$PGPORT" -d "$PGDATABASE" -U "$PGUSER" -t -c "SELECT name FROM public.llms WHERE provider = 'ollama' AND active = true;") || psql_output=""

if [ -z "$psql_output" ]; then
  echo "ollama-pull: No active Ollama models found in database."
else
  echo "ollama-pull: Found models:"
  echo "$psql_output"
  echo "$psql_output" | while IFS= read -r model_name; do
    # Trim whitespace just in case
    model_clean=$(echo "$model_name" | xargs)
    if [ -n "$model_clean" ]; then
      echo "ollama-pull: Pulling $model_clean model from $OLLAMA_HOST_URL..."
      # Construct JSON payload
      json_payload="{\"name\":\"$model_clean\"}"
      # Execute curl command. `set -e` above would abort on the first failed
      # pull before the manual error-handling below runs, so we explicitly
      # tolerate non-zero exits here and rely on the if-check on $? instead.
      curl_exit_code=0
      curl_output=$(curl -sf -X POST "$OLLAMA_HOST_URL/api/pull" -d "$json_payload" 2>&1) || curl_exit_code=$?
      echo "ollama-pull: Curl exit code: $curl_exit_code"
      echo "ollama-pull: Curl output: $curl_output"
      # /api/pull streams NDJSON and can report failures (bad model name,
      # registry errors) inside the body with HTTP 200 — check both the
      # exit code AND the body for an error line, or a typo'd
      # OLLAMA_USER_MODELS entry "succeeds" silently and only surfaces
      # as a LiteLLM 404 at request time.
      if [ $curl_exit_code -ne 0 ] || printf '%s' "$curl_output" | grep -q '"error"'; then
         echo "ollama-pull: ERROR - Failed to pull model $model_clean. See output above." >&2
      fi
      echo # Newline after each pull attempt output
    fi
  done
fi

echo "ollama-pull: Finished model pulling process."

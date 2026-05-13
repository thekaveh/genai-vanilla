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
until curl -s --fail "$OLLAMA_HOST_URL/"; do
  echo "ollama-pull: Waiting for Ollama API..."
  sleep 5
done
echo "ollama-pull: Ollama API is available."

echo "ollama-pull: Fetching active Ollama models from database $PGDATABASE on $PGHOST..."
psql_output=$(PGPASSWORD=$PGPASSWORD psql -h $PGHOST -p $PGPORT -d $PGDATABASE -U $PGUSER -t -c "SELECT name FROM public.llms WHERE provider = 'ollama' AND active = true;")

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
      # Execute curl command
      curl_output=$(curl -s -X POST "$OLLAMA_HOST_URL/api/pull" -d "$json_payload" 2>&1)
      curl_exit_code=$?
      echo "ollama-pull: Curl exit code: $curl_exit_code"
      echo "ollama-pull: Curl output: $curl_output"
      # Check if curl succeeded (exit code 0)
      if [ $curl_exit_code -ne 0 ]; then
         echo "ollama-pull: ERROR - Failed to pull model $model_clean. See output above."
         # Optionally exit here if one failure should stop the process: exit 1
      fi
      echo # Newline after each pull attempt output
    fi
  done
fi

echo "ollama-pull: Finished model pulling process."

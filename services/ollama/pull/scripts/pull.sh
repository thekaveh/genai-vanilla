#!/bin/sh
set -e

# ollama-pull: pulls the active Ollama model set into a container-Ollama
# instance.  The model list is the union of:
#
#   OLLAMA_USER_MODELS   — comma-separated names set by the wizard
#                          (pre-filled in .env.example with the catalog
#                          defaults; overwritten by the wizard with the
#                          user's selection on each wizard run)
#   OLLAMA_CUSTOM_MODELS — free-text extra models added by the user
#
# The two vars are split on commas, trimmed, de-duplicated, and blanks
# dropped.  An empty union means no models to pull; the script logs a
# message and exits 0 cleanly.
#
# NOTE: this script no longer queries the Supabase DB via psql.
# The only required env var is OLLAMA_HOST_URL (the Ollama /api endpoint
# inside the Docker network).

echo "ollama-pull: Starting model pull process..."

# Check required env vars
if [ -z "$OLLAMA_HOST_URL" ]; then
  echo "ollama-pull: Error: OLLAMA_HOST_URL is not set."
  exit 1
fi

echo "ollama-pull: Installing required tools..."
apk add --no-cache curl

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

# Build the model list: union of OLLAMA_USER_MODELS and OLLAMA_CUSTOM_MODELS.
# Split on commas, trim whitespace, drop blanks, de-duplicate (preserve order
# of first occurrence).
_raw_list=$(
  printf '%s\n' "${OLLAMA_USER_MODELS:-}" "${OLLAMA_CUSTOM_MODELS:-}" \
    | tr ',' '\n' \
    | while IFS= read -r _m; do
        _mc=$(printf '%s' "$_m" | xargs 2>/dev/null || printf '%s' "$_m")
        [ -n "$_mc" ] && printf '%s\n' "$_mc"
      done \
    | awk '!seen[$0]++'
)

if [ -z "$_raw_list" ]; then
  echo "ollama-pull: No models configured (OLLAMA_USER_MODELS and OLLAMA_CUSTOM_MODELS are both empty). Nothing to pull."
  echo "ollama-pull: Finished model pulling process."
  exit 0
fi

echo "ollama-pull: Models to pull:"
echo "$_raw_list"

echo "$_raw_list" | while IFS= read -r model_clean; do
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

echo "ollama-pull: Finished model pulling process."

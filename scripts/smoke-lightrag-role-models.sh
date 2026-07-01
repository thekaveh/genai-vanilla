#!/usr/bin/env bash
set -euo pipefail

project="${PROJECT_NAME:-atlas}"
lightrag_url="${LIGHTRAG_URL:-http://localhost:${LIGHTRAG_API_PORT:-63063}}"
api_key="${LIGHTRAG_API_KEY:-}"
extract_model="${LIGHTRAG_EXTRACT_LLM_MODEL:-}"
query_model="${LIGHTRAG_QUERY_LLM_MODEL:-}"

if [ -z "$api_key" ]; then
  echo "LIGHTRAG_API_KEY must be exported from .env before running this smoke." >&2
  echo "Example: set -a; . ./.env; set +a; scripts/smoke-lightrag-role-models.sh" >&2
  exit 2
fi

if [ -z "$extract_model" ] || [ -z "$query_model" ]; then
  echo "Set LIGHTRAG_EXTRACT_LLM_MODEL and LIGHTRAG_QUERY_LLM_MODEL before running this smoke." >&2
  exit 2
fi

echo "[smoke] LightRAG URL: $lightrag_url"
echo "[smoke] expected EXTRACT model: $extract_model"
echo "[smoke] expected QUERY model: $query_model"

echo "[smoke] runtime role environment:"
docker compose -p "$project" exec -T lightrag sh -lc \
  'env | sort | grep -E "^(LLM_MODEL|EXTRACT_LLM_MODEL|KEYWORD_LLM_MODEL|QUERY_LLM_MODEL|EXTRACT_MAX_ASYNC_LLM|QUERY_LLM_TIMEOUT)="'

tmp_doc="$(mktemp)"
cat > "$tmp_doc" <<'DOC'
Atlas is a self-hosted engineering platform. LightRAG is the graph-augmented RAG service. Role-specific LLM configuration lets extraction use a fast model while answers use a stronger model.
DOC

echo "[smoke] uploading one small document"
curl -fsS -X POST "$lightrag_url/documents/upload" \
  -H "Authorization: Bearer $api_key" \
  -F "file=@${tmp_doc};filename=atlas-lightrag-role-smoke.txt" >/tmp/lightrag-upload-response.json

echo "[smoke] waiting 30 seconds for extraction calls to reach LiteLLM"
sleep 30

echo "[smoke] querying LightRAG"
curl -fsS -X POST "$lightrag_url/query" \
  -H "Authorization: Bearer $api_key" \
  -H "Content-Type: application/json" \
  -d '{"query": "/hybrid What does role-specific LightRAG configuration allow Atlas to do?"}' \
  >/tmp/lightrag-query-response.json

echo "[smoke] recent LiteLLM log lines mentioning expected models:"
docker compose -p "$project" logs --since=10m litellm \
  | grep -E "$extract_model|$query_model" \
  | tail -40 || true

echo "[smoke] upload response: /tmp/lightrag-upload-response.json"
echo "[smoke] query response: /tmp/lightrag-query-response.json"
echo "[smoke] pass criteria: the runtime env shows EXTRACT/QUERY values, and LiteLLM logs show requests for both expected models."

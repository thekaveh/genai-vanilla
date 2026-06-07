#!/bin/sh
# LightRAG init container.
# Pattern: alpine + inline apk add (memory: project_init_container_pattern).
# Bash re-exec with sentinel to avoid loop.
set -e

if [ "${INIT_BOOTSTRAPPED:-}" != "1" ]; then
  apk add --no-cache bash curl jq postgresql-client ca-certificates python3 >/dev/null
  export INIT_BOOTSTRAPPED=1
  exec bash -- "$0" "$@"
fi

# ── bash body ─────────────────────────────────────────────────────────────
set -euo pipefail

if [ "${LIGHTRAG_SOURCE:-disabled}" = "disabled" ]; then
  echo "[lightrag-init] LIGHTRAG_SOURCE=disabled, nothing to do"
  exit 0
fi

echo "[lightrag-init] waiting for LiteLLM /v1/models..."
# Timeout matches LightRAG's own start_period (300s). LiteLLM cold start
# (Prisma migrations + worker spawn) can take 2-3 min on first boot; the
# previous 60s ceiling was too aggressive and caused init to bail before
# LiteLLM was ready. Polling progress is printed every 30s.
deadline=$((SECONDS + 300))
last_log=$SECONDS
until curl -fs -H "Authorization: Bearer ${LITELLM_MASTER_KEY:-}" \
            http://litellm:4000/v1/models >/dev/null 2>&1; do
  if [ "$SECONDS" -ge "$deadline" ]; then
    echo "[lightrag-init] FAIL: LiteLLM not reachable after 300s" >&2
    exit 1
  fi
  if [ $((SECONDS - last_log)) -ge 30 ]; then
    echo "[lightrag-init] still waiting for LiteLLM (${SECONDS}s elapsed)..."
    last_log=$SECONDS
  fi
  sleep 2
done

echo "[lightrag-init] resolving model bindings..."
python3 /scripts/resolve-models.py > /app/data/.lightrag-resolved.env

if [ -n "${LIGHTRAG_PG_URI:-}" ]; then
  echo "[lightrag-init] running pgvector migrations..."
  psql "${LIGHTRAG_PG_URI}" -v ON_ERROR_STOP=1 -f /scripts/migrate-pgvector.sql
fi

if [ -n "${LIGHTRAG_NEO4J_URI:-}" ]; then
  echo "[lightrag-init] running Neo4j migrations..."
  # Use Neo4j's HTTP transaction endpoint directly (cypher-shell is not in
  # alpine main; bundling it would inflate the init image significantly).
  cypher_payload=$(jq -Rn --rawfile q /scripts/migrate-neo4j.cypher \
                  '{statements: [{statement: $q}]}')
  http_status=$(curl -fs -o /tmp/neo4j-resp.json -w '%{http_code}' \
    -u "${LIGHTRAG_NEO4J_USERNAME}:${LIGHTRAG_NEO4J_PASSWORD}" \
    -H 'Content-Type: application/json' \
    --data "$cypher_payload" \
    "http://neo4j:7474/db/neo4j/tx/commit" 2>&1) || {
      echo "[lightrag-init] WARN: Neo4j migration HTTP call failed (curl exit $?)" >&2
      echo "[lightrag-init] response: $(cat /tmp/neo4j-resp.json 2>/dev/null)" >&2
    }
  if [ "$http_status" = "200" ]; then
    echo "[lightrag-init] Neo4j migration: OK"
  else
    echo "[lightrag-init] WARN: Neo4j migration returned HTTP $http_status" >&2
    echo "[lightrag-init] response: $(cat /tmp/neo4j-resp.json 2>/dev/null)" >&2
    # Non-fatal — Neo4j may already have the constraints; LightRAG will
    # create them on first write anyway via its NetworkXStorage fallback.
  fi
fi

echo "[lightrag-init] done"

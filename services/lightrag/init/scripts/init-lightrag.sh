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
deadline=$((SECONDS + 60))
until curl -fs -H "Authorization: Bearer ${LITELLM_MASTER_KEY:-}" \
            http://litellm:4000/v1/models >/dev/null 2>&1; do
  if [ "$SECONDS" -ge "$deadline" ]; then
    echo "[lightrag-init] FAIL: LiteLLM not reachable after 60s" >&2
    exit 1
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
  # Use cypher-shell from apk (not installed by default — install on demand).
  if ! command -v cypher-shell >/dev/null 2>&1; then
    apk add --no-cache cypher-shell >/dev/null 2>&1 || {
      # cypher-shell not in alpine main; fall back to a curl-based HTTP submission.
      curl -fs -u "${LIGHTRAG_NEO4J_USERNAME}:${LIGHTRAG_NEO4J_PASSWORD}" \
        -H 'Content-Type: application/json' \
        --data "$(jq -Rn --rawfile q /scripts/migrate-neo4j.cypher \
                  '{statements: [{statement: $q}]}')" \
        "http://neo4j:7474/db/neo4j/tx/commit" >/dev/null
    }
  fi
fi

echo "[lightrag-init] done"

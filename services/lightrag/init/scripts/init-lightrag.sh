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

# LiteLLM readiness is guaranteed by compose: lightrag-init's compose entry
# declares `depends_on: litellm: condition: service_healthy`, so by the time
# this script runs LiteLLM has already passed its /health/liveliness probe.
# No in-script poll loop needed (matches the hermes-init pattern).

echo "[lightrag-init] resolving model bindings..."
# Write to /app/data/.env so LightRAG's startup loader picks it up. LightRAG
# WARNs at boot when the working directory lacks a .env file — this satisfies
# that requirement and provides the per-instance LLM/embedding model bindings.
python3 /scripts/resolve-models.py > /app/data/.env

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
    "http://neo4j-graph-db:7474/db/neo4j/tx/commit" 2>&1) || {
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

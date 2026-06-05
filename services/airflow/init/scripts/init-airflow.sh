#!/usr/bin/env bash
# init-airflow.sh — one-shot init container for Airflow.
#
# Responsibilities (idempotent — re-runs are no-ops):
# 1. Create the `airflow` database in Supabase Postgres if missing.
# 2. Create the `${AIRFLOW_DB_USER}` Postgres role if missing.
# 3. Run `airflow db migrate`.
# 4. Create the admin user.
# 5. Seed Connection objects for every sibling service whose source is
#    not 'disabled'.
set -euo pipefail

echo "==> airflow-init: ensuring airflow database exists"
# Use Supabase admin creds to CREATE DATABASE if absent. supabase-db
# entrypoint runs as 'postgres' superuser; we connect via the
# Supabase-managed db with the configured admin user.
export PGPASSWORD="${SUPABASE_DB_PASSWORD}"
psql -h supabase-db -U "${SUPABASE_DB_USER}" -d "${SUPABASE_DB_NAME}" -tAc \
     "SELECT 1 FROM pg_database WHERE datname='airflow'" | grep -q 1 \
  || psql -h supabase-db -U "${SUPABASE_DB_USER}" -d "${SUPABASE_DB_NAME}" \
       -c "CREATE DATABASE airflow"

echo "==> airflow-init: ensuring airflow role exists"
psql -h supabase-db -U "${SUPABASE_DB_USER}" -d postgres -tAc \
     "SELECT 1 FROM pg_roles WHERE rolname='${AIRFLOW_DB_USER}'" | grep -q 1 \
  || psql -h supabase-db -U "${SUPABASE_DB_USER}" -d postgres \
       -c "CREATE ROLE ${AIRFLOW_DB_USER} WITH LOGIN PASSWORD '${AIRFLOW_DB_PASSWORD}'"
# Re-apply the password every run so that AIRFLOW_DB_PASSWORD rotations
# in .env are picked up — CREATE ROLE only runs the first time.
# Idempotent: setting the role's password to its current value is a no-op.
psql -h supabase-db -U "${SUPABASE_DB_USER}" -d postgres \
     -c "ALTER ROLE ${AIRFLOW_DB_USER} WITH PASSWORD '${AIRFLOW_DB_PASSWORD}'"
psql -h supabase-db -U "${SUPABASE_DB_USER}" -d postgres \
     -c "GRANT ALL PRIVILEGES ON DATABASE airflow TO ${AIRFLOW_DB_USER}"
# Postgres 15+ (the stack ships supabase/postgres:17.x) tightened the
# public-schema default: ALL PRIVILEGES on the database does NOT include
# CREATE on `public` — only the database OWNER has that, via the magic
# pg_database_owner role. CREATE DATABASE made supabase_admin the owner,
# so airflow's `db migrate` would fail with "permission denied for schema
# public" on every cold start. Re-owning the database to airflow flips
# pg_database_owner over (idempotent — `ALTER ... OWNER TO already_owner`
# is a no-op).
psql -h supabase-db -U "${SUPABASE_DB_USER}" -d postgres \
     -c "ALTER DATABASE airflow OWNER TO ${AIRFLOW_DB_USER}"
unset PGPASSWORD

echo "==> airflow-init: running airflow db migrate"
airflow db migrate

echo "==> airflow-init: creating admin user (idempotent)"
# Capture stderr so a real failure surfaces in container logs instead of
# being hidden by the "already exists" success message. The CLI prints
# `airflow.exceptions.AirflowException: Cannot create user`-class errors
# on real failure (e.g. FabAuthManager not configured) vs "User admin
# already exists" on the idempotent re-run case. Only the latter is OK.
create_output=$(airflow users create \
  --username admin \
  --firstname Admin \
  --lastname User \
  --role Admin \
  --email admin@localhost \
  --password "${AIRFLOW_ADMIN_PASSWORD}" 2>&1) || true
if echo "$create_output" | grep -qE "already exists|already a user"; then
  echo "(admin user already exists — skipping)"
elif echo "$create_output" | grep -qiE "error|exception|traceback"; then
  echo "airflow-init: ERROR during admin user creation:" >&2
  echo "$create_output" >&2
  exit 1
else
  echo "$create_output"
fi

echo "==> airflow-init: seeding Connections (gated on sibling source)"

# Helper: idempotent add (delete + add to update on second run)
add_conn() {
  local conn_id=$1; shift
  airflow connections delete "$conn_id" >/dev/null 2>&1 || true
  airflow connections add "$conn_id" "$@"
}

# Orphan-cleanup pass: drop any source-gated Connection up front. The
# guarded add_conn calls below will re-create the ones still active. This
# prevents stale entries from a prior run where the sibling source was
# `container` from sitting in the metadata DB after the user flips it
# back to `disabled` — orphan Connections would point at dead DNS names
# and confuse DAGs that reference them.
for orphan in spark_default minio_default weaviate_default neo4j_default; do
  airflow connections delete "$orphan" >/dev/null 2>&1 || true
done

# Gating convention: every gate uses `= "container"` (NOT `!= "disabled"`).
# The `!= "disabled"` form silently includes the `localhost` source variant
# for services that support it (weaviate / neo4j), which would seed a
# Connection pointing at the in-Compose DNS name (e.g. `weaviate:8080`)
# that does NOT resolve when the user is running the service on the host.
# In-container DNS is only valid when source == container. For host-side
# variants, the user must manage Connection objects manually (or extend
# this script to read the LOCALHOST URL override env vars).
#
# LiteLLM + Postgres + Redis are unconditional: LiteLLM is locked
# always-on (services/litellm/service.yml: "Locked. Mandatory."), Postgres
# is a required dependency, and Redis ships as a container-only always-on
# service (services/redis/service.yml).

if [ "${SPARK_SOURCE}" = "container" ]; then
  add_conn spark_default --conn-type spark --conn-host spark-master --conn-port 7077
fi

if [ "${MINIO_SOURCE}" = "container" ]; then
  add_conn minio_default \
    --conn-type aws \
    --conn-extra "{\"endpoint_url\": \"http://minio:9000\", \"aws_access_key_id\": \"${MINIO_ROOT_USER}\", \"aws_secret_access_key\": \"${MINIO_ROOT_PASSWORD}\"}"
fi

add_conn litellm_default \
  --conn-type openai \
  --conn-host http://litellm:4000 \
  --conn-password "${LITELLM_MASTER_KEY}" \
  --conn-extra '{"api_base": "http://litellm:4000/v1"}'

# NOTE: postgres_supabase intentionally uses the SUPABASE_DB_USER (admin)
# credentials today. The .env declares SUPABASE_DB_APP_USER / _PASSWORD
# for a least-privilege application-tier user, but supabase-db-init's
# scripts do not actually CREATE that role yet — switching this seed to
# app_user without first creating the role would break every DAG that
# uses postgres_supabase. Tracked as a known follow-up in CHANGELOG —
# the safer migration is: (1) wire app_user creation into supabase-db-init,
# (2) flip this seed + add an Airflow Variable for the admin escape hatch.
add_conn postgres_supabase \
  --conn-type postgres --conn-host supabase-db --conn-port 5432 \
  --conn-schema "${SUPABASE_DB_NAME}" \
  --conn-login "${SUPABASE_DB_USER}" \
  --conn-password "${SUPABASE_DB_PASSWORD}"

if [ "${WEAVIATE_SOURCE}" = "container" ]; then
  add_conn weaviate_default --conn-type weaviate --conn-host http://weaviate:8080
fi

# NOTE: var name is NEO4J_GRAPH_DB_SOURCE (NOT NEO4J_SOURCE — the latter
# does not exist in .env.example and was silently undefined → "disabled"
# → neo4j_default never seeded prior to this fix).
# Compose service id is `neo4j-graph-db` (NOT `neo4j`); every other
# in-stack consumer uses bolt://neo4j-graph-db:7687. Credentials come
# from GRAPH_DB_USER / GRAPH_DB_PASSWORD (the Neo4j family's canonical
# env vars), passed through compose.yml's airflow-init environment.
if [ "${NEO4J_GRAPH_DB_SOURCE}" = "container" ]; then
  add_conn neo4j_default \
    --conn-type neo4j \
    --conn-host "bolt://neo4j-graph-db" \
    --conn-port 7687 \
    --conn-login "${GRAPH_DB_USER}" \
    --conn-password "${GRAPH_DB_PASSWORD}"
fi

add_conn redis_default --conn-type redis --conn-host redis --conn-port 6379 --conn-password "${REDIS_PASSWORD}"

echo "==> airflow-init: complete"

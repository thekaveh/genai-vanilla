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
psql -h supabase-db -U "${SUPABASE_DB_USER}" -d postgres \
     -c "GRANT ALL PRIVILEGES ON DATABASE airflow TO ${AIRFLOW_DB_USER}"
unset PGPASSWORD

echo "==> airflow-init: running airflow db migrate"
airflow db migrate

echo "==> airflow-init: creating admin user (idempotent)"
airflow users create \
  --username admin \
  --firstname Admin \
  --lastname User \
  --role Admin \
  --email admin@localhost \
  --password "${AIRFLOW_ADMIN_PASSWORD}" \
  || echo "(admin user already exists — skipping)"

echo "==> airflow-init: seeding Connections (gated on sibling source)"

# Helper: idempotent add (delete + add to update on second run)
add_conn() {
  local conn_id=$1; shift
  airflow connections delete "$conn_id" >/dev/null 2>&1 || true
  airflow connections add "$conn_id" "$@"
}

if [ "${SPARK_SOURCE}" = "container" ]; then
  add_conn spark_default --conn-type spark --conn-host spark-master --conn-port 7077
fi

if [ "${MINIO_SOURCE}" = "container" ]; then
  add_conn minio_default \
    --conn-type aws \
    --conn-extra "{\"endpoint_url\": \"http://minio:9000\", \"aws_access_key_id\": \"${MINIO_ROOT_USER}\", \"aws_secret_access_key\": \"${MINIO_ROOT_PASSWORD}\"}"
fi

if [ "${LITELLM_SOURCE}" != "disabled" ]; then
  add_conn litellm_default \
    --conn-type openai \
    --conn-host http://litellm:4000 \
    --conn-password "${LITELLM_MASTER_KEY}" \
    --conn-extra '{"api_base": "http://litellm:4000/v1"}'
fi

add_conn postgres_supabase \
  --conn-type postgres --conn-host supabase-db --conn-port 5432 \
  --conn-schema "${SUPABASE_DB_NAME}" \
  --conn-login "${SUPABASE_DB_USER}" \
  --conn-password "${SUPABASE_DB_PASSWORD}"

if [ "${WEAVIATE_SOURCE}" != "disabled" ]; then
  add_conn weaviate_default --conn-type weaviate --conn-host http://weaviate:8080
fi

if [ "${NEO4J_SOURCE}" != "disabled" ]; then
  add_conn neo4j_default --conn-type neo4j --conn-host bolt://neo4j --conn-port 7687
fi

if [ "${REDIS_SOURCE}" != "disabled" ]; then
  add_conn redis_default --conn-type redis --conn-host redis --conn-port 6379
fi

echo "==> airflow-init: complete"

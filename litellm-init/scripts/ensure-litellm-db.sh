#!/bin/sh
set -e

# Provisions a dedicated `litellm` database on the existing Supabase Postgres
# server. Same host (PGHOST=supabase-db), same credentials — different logical
# database. LiteLLM's Prisma-managed tables stay isolated from Supabase's
# schema; LiteLLM's prod docs explicitly recommend this layout.
# We connect to the maintenance `postgres` database (every Postgres server has
# one) because CREATE DATABASE cannot run from inside the database it creates.

echo "litellm-init: Starting LiteLLM database provisioning..."

if [ -z "$PGHOST" ] || [ -z "$PGUSER" ] || [ -z "$PGPASSWORD" ] || [ -z "$LITELLM_DB_NAME" ]; then
  echo "litellm-init: Error: One or more required environment variables are not set."
  echo "PGHOST=$PGHOST, PGUSER=$PGUSER, PGPASSWORD=[set], LITELLM_DB_NAME=$LITELLM_DB_NAME"
  exit 1
fi

echo "litellm-init: Installing required tools..."
apk add --no-cache postgresql-client

echo "litellm-init: Waiting for database to be ready..."
sleep 5
until PGPASSWORD=$PGPASSWORD psql -h $PGHOST -p $PGPORT -d postgres -U $PGUSER -c '\q' 2>/dev/null; do
  echo "litellm-init: Waiting for database..."
  sleep 5
done
echo "litellm-init: Database is available."

echo "litellm-init: Ensuring '$LITELLM_DB_NAME' database exists..."
db_exists=$(PGPASSWORD=$PGPASSWORD psql -h $PGHOST -p $PGPORT -d postgres -U $PGUSER -tAc "SELECT 1 FROM pg_database WHERE datname='$LITELLM_DB_NAME';")

if [ "$db_exists" = "1" ]; then
  echo "litellm-init: Database '$LITELLM_DB_NAME' already exists, skipping creation."
else
  echo "litellm-init: Creating database '$LITELLM_DB_NAME'..."
  PGPASSWORD=$PGPASSWORD psql -h $PGHOST -p $PGPORT -d postgres -U $PGUSER -c "CREATE DATABASE \"$LITELLM_DB_NAME\";"
  echo "litellm-init: Database '$LITELLM_DB_NAME' created."
fi

echo "litellm-init: LiteLLM Prisma migrations will run on first LiteLLM container start (USE_PRISMA_MIGRATE=True)."
echo "litellm-init: Provisioning complete."

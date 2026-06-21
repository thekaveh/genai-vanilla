#!/bin/sh
# Restore the Postgres dump from a given (or latest) S3 backup timestamp.
set -eu
: "${SUPABASE_DB_USER:?required}"; : "${SUPABASE_DB_PASSWORD:?required}"; : "${SUPABASE_DB_NAME:?required}"
: "${MINIO_ROOT_USER:?required}"; : "${MINIO_ROOT_PASSWORD:?required}"
BUCKET="${BACKUP_BUCKET:-atlas-backups}"
mc alias set s3 "${BACKUP_S3_ALIAS_URL:-http://minio:9000}" "$MINIO_ROOT_USER" "$MINIO_ROOT_PASSWORD"

TS="${BACKUP_TIMESTAMP:-}"
if [ -z "$TS" ]; then
  TS="$(mc ls "s3/${BUCKET}/" | awk '{print $NF}' | tr -d / | sort | tail -1)"
fi
[ -n "$TS" ] || { echo "restore: no backups found in s3/${BUCKET}/" >&2; exit 1; }
echo "restore: using backup ${TS}"
mkdir -p /tmp/restore
mc cp "s3/${BUCKET}/${TS}/postgres.dump" /tmp/restore/postgres.dump
echo "restore: pg_restore into ${SUPABASE_DB_NAME} (clean)..."
PGPASSWORD="$SUPABASE_DB_PASSWORD" pg_restore -h supabase-db -U "$SUPABASE_DB_USER" -d "$SUPABASE_DB_NAME" --clean --if-exists /tmp/restore/postgres.dump
echo "restore: done"

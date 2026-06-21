#!/bin/sh
# Restore the Postgres dump from a given (or latest) S3 backup timestamp.
set -eu
: "${SUPABASE_DB_USER:?required}"; : "${SUPABASE_DB_PASSWORD:?required}"; : "${SUPABASE_DB_NAME:?required}"
: "${MINIO_ROOT_USER:?required}"; : "${MINIO_ROOT_PASSWORD:?required}"
BUCKET="${BACKUP_BUCKET:-atlas-backups}"
mc alias set s3 "${BACKUP_S3_ALIAS_URL:-http://minio:9000}" "$MINIO_ROOT_USER" "$MINIO_ROOT_PASSWORD"

listing="$(mc ls "s3/${BUCKET}/" 2>&1)" || { echo "restore: cannot list s3/${BUCKET}/: ${listing}" >&2; exit 1; }
TS="${BACKUP_TIMESTAMP:-}"
if [ -z "$TS" ]; then
    TS="$(printf '%s\n' "$listing" | awk '{print $NF}' | tr -d / | grep -E '^[0-9]{8}_[0-9]{6}$' | sort | tail -1)"
fi
[ -n "$TS" ] || { echo "restore: no backups found in s3/${BUCKET}/" >&2; exit 1; }
echo "restore: using backup ${TS}"
rm -rf /tmp/restore && mkdir -p /tmp/restore
mc cp "s3/${BUCKET}/${TS}/postgres.dump" /tmp/restore/postgres.dump
echo "restore: pg_restore into ${SUPABASE_DB_NAME} (clean)..."
PGPASSWORD="$SUPABASE_DB_PASSWORD" pg_restore -h supabase-db -U "$SUPABASE_DB_USER" -d "$SUPABASE_DB_NAME" --clean --if-exists /tmp/restore/postgres.dump
echo "restore: done"

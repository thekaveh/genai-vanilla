#!/bin/sh
# Cross-service backup: Postgres dump + named-volume tarballs -> S3 (MinIO or external).
# One-shot; intended to be invoked via `docker compose run --rm backup`.
set -eu

: "${SUPABASE_DB_USER:?required}"; : "${SUPABASE_DB_PASSWORD:?required}"; : "${SUPABASE_DB_NAME:?required}"
: "${MINIO_ROOT_USER:?required}"; : "${MINIO_ROOT_PASSWORD:?required}"
BUCKET="${BACKUP_BUCKET:-atlas-backups}"
TS="${BACKUP_TIMESTAMP:-$(date +%Y%m%d_%H%M%S)}"
WORK=/tmp/backup
mkdir -p "$WORK"

echo "backup: pg_dump ${SUPABASE_DB_NAME}..."
PGPASSWORD="$SUPABASE_DB_PASSWORD" pg_dump -h supabase-db -U "$SUPABASE_DB_USER" -d "$SUPABASE_DB_NAME" -Fc -f "$WORK/postgres.dump"

echo "backup: snapshot mounted volumes..."
# Volumes to snapshot are bind-mounted read-only at /volumes/<name> by the fragment.
for d in /volumes/*; do
  [ -d "$d" ] || continue
  name="$(basename "$d")"
  tar czf "$WORK/${name}.tar.gz" -C "$d" .
  echo "backup: archived ${name}"
done

echo "backup: push to s3://${BUCKET}/${TS}/..."
mc alias set s3 "${BACKUP_S3_ALIAS_URL:-http://minio:9000}" "$MINIO_ROOT_USER" "$MINIO_ROOT_PASSWORD"
mc mb --ignore-existing "s3/${BUCKET}"
mc cp --recursive "$WORK/" "s3/${BUCKET}/${TS}/"
echo "backup: done -> s3/${BUCKET}/${TS}/"

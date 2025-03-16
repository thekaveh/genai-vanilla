#!/bin/bash

# This script creates a database backup

SCRIPT_DIR="$(dirname "$(readlink -f "$0")")"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="${SCRIPT_DIR}/../snapshot/backup_${TIMESTAMP}.sql"

echo "Creating database backup to ${BACKUP_FILE}..."

pg_dump -U "${POSTGRES_USER}" -d "${POSTGRES_DB}" > "${BACKUP_FILE}"

echo "Backup completed."

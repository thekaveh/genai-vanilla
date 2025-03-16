#!/bin/bash

# This script restores a database from the latest backup file found in the snapshot directory

SCRIPT_DIR="$(dirname "$(readlink -f "$0")")"
SNAPSHOT_DIR="${SCRIPT_DIR}/../snapshot"

# Find the latest backup file
LATEST_BACKUP=$(find "${SNAPSHOT_DIR}" -name "backup_*.sql" -type f -printf "%T@ %p\n" | sort -n | tail -1 | cut -d' ' -f2)

# If a backup file exists, restore it
if [ -n "${LATEST_BACKUP}" ] && [ -f "${LATEST_BACKUP}" ]; then
    echo "Restoring database from ${LATEST_BACKUP}..."
    psql -U "${SQL_DB_USER}" -d "${SQL_DB_NAME}" < "${LATEST_BACKUP}"
    echo "Database restored successfully."
else
    echo "No backup file found. Skipping restore."
fi

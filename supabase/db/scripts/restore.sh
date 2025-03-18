#!/bin/bash

# This script restores a database from the latest backup file found in the snapshot directory

# Use the container's mounted snapshot directory
SNAPSHOT_DIR="/snapshot"

# Ensure snapshot directory exists
mkdir -p "${SNAPSHOT_DIR}"

# Find the latest backup file
LATEST_BACKUP=$(find "${SNAPSHOT_DIR}" -name "backup_*.sql" -type f -printf "%T@ %p\n" | sort -n | tail -1 | cut -d' ' -f2)

# If a backup file exists, restore it
if [ -n "${LATEST_BACKUP}" ] && [ -f "${LATEST_BACKUP}" ]; then
    echo "Restoring database from ${LATEST_BACKUP}..."
    psql -U "${POSTGRES_USER}" -d "${POSTGRES_DB}" < "${LATEST_BACKUP}"
    echo "Database restored successfully."
else
    echo "No backup file found. Skipping restore."
fi
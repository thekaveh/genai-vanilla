#!/bin/bash

# This script creates a database backup

# Use the container's mounted snapshot directory
SNAPSHOT_DIR="/snapshot"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="${SNAPSHOT_DIR}/backup_${TIMESTAMP}.sql"

# Ensure snapshot directory exists
mkdir -p "${SNAPSHOT_DIR}"

echo "Creating database backup to ${BACKUP_FILE}..."

pg_dump -U "${SQL_DB_USER}" -d "${SQL_DB_NAME}" > "${BACKUP_FILE}"

echo "Backup completed at ${BACKUP_FILE}"
echo "This file is also available on your host at ./sql-db/snapshot/backup_${TIMESTAMP}.sql"

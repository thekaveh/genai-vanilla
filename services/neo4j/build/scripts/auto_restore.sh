#!/bin/bash

# This script automatically checks for backup files in the snapshot directory
# and restores the latest one if it exists.

# Ensure snapshot directory exists
mkdir -p /snapshot

echo "Checking for Neo4j backups to restore..."

# Look for the latest backup in the snapshot directory
LATEST_BACKUP=$(find /snapshot -name "backup_*.dump" -type f -printf "%T@ %p\n" 2>/dev/null | sort -n | tail -1 | cut -d' ' -f2)

# If a backup file exists, restore it
if [ -n "${LATEST_BACKUP}" ] && [ -f "${LATEST_BACKUP}" ]; then
  echo "Found backup file: ${LATEST_BACKUP}"
  echo "Automatically restoring Neo4j database from backup..."

  # Get backup filename without path
  BACKUP_FILENAME=$(basename "${LATEST_BACKUP}")

  # Note: this script runs from docker-entrypoint-wrapper.sh BEFORE the
  # neo4j server is started, so no `neo4j stop` dance is needed here.
  # (Earlier revisions guarded with `if neo4j status | grep -q running`,
  # but the check was unreachable in this execution path.)

  # Restore the database
  neo4j-admin database restore neo4j --from-path="/snapshot" --input-name="${BACKUP_FILENAME}" --force

  echo "Database automatically restored successfully."
else
  echo "No backup file found. Skipping automatic restore."
fi
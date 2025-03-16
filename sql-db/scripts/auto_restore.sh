#!/bin/bash

# This script automatically checks for backup files in the snapshot directory
# and restores the latest one if it exists.

# Only run if the database has been initialized (to avoid running during first-time setup)
if [ -f "${PGDATA}/PG_VERSION" ]; then
  echo "PostgreSQL data directory already exists, checking for backups to restore..."
  
  # Look for the latest backup in the snapshot directory
  if [ -d "/snapshot" ]; then
    LATEST_BACKUP=$(find /snapshot -name "backup_*.sql" -type f -printf "%T@ %p\n" | sort -n | tail -1 | cut -d' ' -f2)
    
    # If a backup file exists, restore it
    if [ -n "${LATEST_BACKUP}" ] && [ -f "${LATEST_BACKUP}" ]; then
      echo "Found backup file: ${LATEST_BACKUP}"
      echo "Automatically restoring database from backup..."
      psql -U "${POSTGRES_USER}" -d "${POSTGRES_DB}" < "${LATEST_BACKUP}"
      echo "Database automatically restored successfully."
    else
      echo "No backup files found in snapshot directory. Skipping automatic restore."
    fi
  else
    echo "Snapshot directory not found. Skipping automatic restore."
  fi
else
  echo "First-time PostgreSQL initialization - skipping automatic restore."
fi
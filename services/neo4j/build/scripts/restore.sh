#!/bin/bash

# This script restores a Neo4j database from the latest backup file

SCRIPT_DIR="$(dirname "$(readlink -f "$0")")"
SNAPSHOT_DIR="${SCRIPT_DIR}/../snapshot"

# Ensure snapshot directory exists
mkdir -p "${SNAPSHOT_DIR}"

# Find the latest backup file
LATEST_BACKUP=$(find "${SNAPSHOT_DIR}" -name "backup_*.dump" -type f -printf "%T@ %p\n" 2>/dev/null | sort -n | tail -1 | cut -d' ' -f2)

# If a backup file exists, restore it
if [ -n "${LATEST_BACKUP}" ] && [ -f "${LATEST_BACKUP}" ]; then
    echo "Found backup file: ${LATEST_BACKUP}"
    echo "Restoring Neo4j database from backup..."
    
    # Stop Neo4j service
    neo4j stop
    
    # Wait for Neo4j to stop
    echo "Waiting for Neo4j to stop..."
    until ! neo4j status | grep -q "Neo4j is running"; do
      sleep 1
    done
    
    # Get backup filename without path
    BACKUP_FILENAME=$(basename "${LATEST_BACKUP}")
    
    # Restore the database
    neo4j-admin database restore neo4j --from-path="${SNAPSHOT_DIR}" --input-name="${BACKUP_FILENAME}" --force
    
    # Start Neo4j service
    neo4j start
    
    echo "Database restored successfully."
    echo "Neo4j service restarted."
else
    echo "No backup file found. Skipping restore."
fi
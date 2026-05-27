#!/bin/bash
set -euo pipefail

# This script creates a backup of Neo4j database

# /snapshot is the bind-mount target declared in services/neo4j/compose.yml
# (./build/snapshot:/snapshot). Earlier revisions derived the path from
# $SCRIPT_DIR, which resolved to /usr/local/snapshot (an unmounted
# directory inside the container) and silently lost every backup on
# container restart. Hardcoding the mount target is the simplest guard.
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR=/snapshot
BACKUP_FILE="${BACKUP_DIR}/backup_${TIMESTAMP}.dump"

# Ensure backup directory exists
mkdir -p "${BACKUP_DIR}"

echo "Creating Neo4j database backup to ${BACKUP_FILE}..."

# Stop Neo4j service temporarily to ensure consistent backup
neo4j stop

# Wait for Neo4j to stop
echo "Waiting for Neo4j to stop..."
until ! neo4j status | grep -q "Neo4j is running"; do
  sleep 1
done

# Perform the backup using neo4j-admin
neo4j-admin database dump neo4j --to-path="${BACKUP_DIR}" --output-name="backup_${TIMESTAMP}.dump"

# Restart Neo4j service
neo4j start

echo "Backup completed and stored at: ${BACKUP_FILE}"
echo "Neo4j service restarted."
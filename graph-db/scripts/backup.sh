#!/bin/bash

# This script creates a backup of Neo4j database

SCRIPT_DIR="$(dirname "$(readlink -f "$0")")"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="${SCRIPT_DIR}/../snapshot"
BACKUP_FILE="${BACKUP_DIR}/backup_${TIMESTAMP}.dump"

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
#!/bin/bash

# This script restores a Neo4j database from the latest backup file

# /snapshot is the bind-mount target from services/neo4j/compose.yml; the
# previous ${SCRIPT_DIR}/../snapshot expression resolved to
# /usr/local/snapshot inside the container and never saw the host volume.
SNAPSHOT_DIR=/snapshot

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
    
    
    # Restore the database. 5.x community has no `database restore`
    # subcommand (that pairs with enterprise `backup`); dumps are
    # restored with `database load`. --from-stdin sidesteps load's
    # <database>.dump naming requirement for our timestamped files.
    if neo4j-admin database load neo4j --from-stdin --overwrite-destination < "${LATEST_BACKUP}"; then
        restore_ok=1
    else
        restore_ok=0
        echo "ERROR: restore from ${LATEST_BACKUP} FAILED (load exited non-zero)." >&2
        echo "ERROR: the neo4j database may be in a partially-overwritten state; inspect before trusting data." >&2
    fi

    # Start Neo4j service (even after a failed load, so the server isn't left stopped)
    neo4j start

    if [ "${restore_ok}" -eq 1 ]; then
        echo "Database restored successfully."
        echo "Neo4j service restarted."
    else
        echo "Neo4j service restarted WITHOUT a successful restore." >&2
        exit 1
    fi
else
    echo "No backup file found. Skipping restore."
fi
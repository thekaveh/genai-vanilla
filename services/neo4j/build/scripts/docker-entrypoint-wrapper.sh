#!/bin/bash

# This is a wrapper around the original Neo4j docker-entrypoint.sh script
# that adds automatic backup restoration

# Run the auto-restore script - will only do anything if a backup exists
/usr/local/bin/auto_restore.sh

# Then continue with the normal Neo4j entrypoint script
exec /startup/docker-entrypoint.sh "$@"
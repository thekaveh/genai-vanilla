#!/bin/bash

# This is a wrapper around the original Neo4j docker-entrypoint.sh script
# that adds automatic backup restoration

# Run the auto-restore script - will only do anything if a backup exists.
# auto_restore.sh exits non-zero when a restore was attempted but the
# `neo4j-admin database load` failed (leaving the DB possibly partially
# overwritten). Honor that signal: refuse to start on top of a half-restored
# database rather than silently booting it with the failure swallowed.
if ! /usr/local/bin/auto_restore.sh; then
  echo "neo4j: auto-restore failed; refusing to start on a possibly partially-restored database" >&2
  exit 1
fi

# Then continue with the normal Neo4j entrypoint script
exec /startup/docker-entrypoint.sh "$@"
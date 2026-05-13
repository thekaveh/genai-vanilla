#!/bin/sh
set -e # Exit immediately if a command exits with a non-zero status.

# Check required env vars are passed from compose file
if [ -z "$PGHOST" ] || [ -z "$PGUSER" ] || [ -z "$PGPASSWORD" ] || [ -z "$PGDATABASE" ]; then
  echo "db-init-runner: Error: One or more database connection environment variables are not set."
  exit 1
fi

echo "db-init-runner: Waiting for database service $PGHOST..."
# Use pg_isready to wait for the database server to accept connections
until pg_isready -h "$PGHOST" -U "$PGUSER" -d "$PGDATABASE" -q; do
  echo "db-init-runner: Database unavailable - sleeping 1s"
  sleep 1
done

echo "db-init-runner: Database is ready. Running post-initialization scripts from /scripts/..."

# Loop through SQL files in mounted directory in alphabetical/numerical order
# Use find to handle potential spaces or special characters in filenames (though unlikely here)
# and sort to ensure numerical order (01, 02, ..., 10, etc.)
find /scripts -maxdepth 1 -name '*.sql' -print | sort | while read f; do
  if [ -f "$f" ]; then
    echo "db-init-runner: Running $f..."
    # Execute script using psql, stop on error
    psql -v ON_ERROR_STOP=1 --host "$PGHOST" --username "$PGUSER" --dbname "$PGDATABASE" -a -f "$f"
  fi
done

echo "db-init-runner: All post-initialization scripts finished successfully."

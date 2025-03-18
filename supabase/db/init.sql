-- Enable extensions if not already enabled
CREATE EXTENSION IF NOT EXISTS pgvector;
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS postgis;

-- Create users table as an example
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT now()
);

-- Add authentication entry to pg_hba.conf to allow all connections
\connect postgres
\set pgdata `echo "$PGDATA"`
\set hba_path :pgdata '/pg_hba.conf'
\! echo "host all all 0.0.0.0/0 trust" >> /var/lib/postgresql/data/pg_hba.conf
SELECT pg_reload_conf();
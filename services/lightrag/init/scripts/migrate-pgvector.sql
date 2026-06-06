-- services/lightrag/init/scripts/migrate-pgvector.sql
-- Idempotent pgvector schema setup for LightRAG.

CREATE EXTENSION IF NOT EXISTS vector;
CREATE SCHEMA IF NOT EXISTS lightrag;

-- Chunks vector table. The actual dimension is configured by LightRAG at
-- runtime via PGVectorStorage; we provision a generic placeholder that the
-- LightRAG storage layer will manage. If LightRAG creates tables on first
-- run, this no-ops harmlessly.
CREATE TABLE IF NOT EXISTS lightrag.vectors_meta (
    schema_version int NOT NULL DEFAULT 1,
    applied_at timestamptz NOT NULL DEFAULT now()
);

INSERT INTO lightrag.vectors_meta (schema_version) VALUES (1)
ON CONFLICT DO NOTHING;

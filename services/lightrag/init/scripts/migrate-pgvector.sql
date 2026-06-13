-- services/lightrag/init/scripts/migrate-pgvector.sql
-- Idempotent pgvector schema setup for LightRAG.

CREATE EXTENSION IF NOT EXISTS vector;
CREATE SCHEMA IF NOT EXISTS lightrag;

-- Chunks vector table. The actual dimension is configured by LightRAG at
-- runtime via PGVectorStorage; we provision a generic placeholder that the
-- LightRAG storage layer will manage. If LightRAG creates tables on first
-- run, this no-ops harmlessly.
-- schema_version is the PK: without a unique constraint, ON CONFLICT
-- can never fire and this table grew one row per `docker compose up`.
CREATE TABLE IF NOT EXISTS lightrag.vectors_meta (
    schema_version int PRIMARY KEY,
    applied_at timestamptz NOT NULL DEFAULT now()
);

-- Heal tables created by the pre-PK version of this script: collapse
-- duplicates, then add the constraint if it's still missing.
DO $$ BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conrelid = 'lightrag.vectors_meta'::regclass
          AND contype = 'p'
    ) THEN
        DELETE FROM lightrag.vectors_meta a
        USING lightrag.vectors_meta b
        WHERE a.ctid < b.ctid AND a.schema_version = b.schema_version;
        ALTER TABLE lightrag.vectors_meta ADD PRIMARY KEY (schema_version);
    END IF;
END $$;

INSERT INTO lightrag.vectors_meta (schema_version) VALUES (1)
ON CONFLICT (schema_version) DO NOTHING;

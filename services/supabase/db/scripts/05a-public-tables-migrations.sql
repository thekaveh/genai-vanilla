-- 05a-public-tables-migrations.sql
-- Idempotent migrations on top of 05-public-tables.sql.
--
-- Runs alphabetically after 05- and before 06- (permissions), so the
-- corrected constraints are in place before anything queries the table.
--
-- Why this exists:
--   The original ``public.llms`` table had ``UNIQUE (name)``. That
--   blocks distinct rows for the same model name across providers
--   (e.g. ``gpt-4o`` from openai and ``openrouter/openai/gpt-4o`` from
--   openrouter, or two providers ever offering a model with the same
--   bare name). The right shape is ``UNIQUE (provider, name)``.
--
-- This migration is safe to re-run on existing DBs.

-- 1. Drop the old single-column unique constraint if it's still there.
ALTER TABLE public.llms DROP CONSTRAINT IF EXISTS llms_name_key;

-- 2. Add the (provider, name) composite unique constraint, idempotent.
-- ``conname`` alone isn't a unique key in pg_constraint — the same
-- name can exist on different tables. Scope by ``conrelid`` so an
-- unrelated table's ``llms_provider_name_key`` constraint can't make
-- this guard skip the ALTER on public.llms.
DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_constraint
    WHERE conname = 'llms_provider_name_key'
      AND conrelid = 'public.llms'::regclass
  ) THEN
    ALTER TABLE public.llms
      ADD CONSTRAINT llms_provider_name_key UNIQUE (provider, name);
  END IF;
END $$;

-- 3. Backfill new columns onto pre-existing public.llms tables.
--   ``description``, ``size_gb``, ``context_window`` (added 2025-07-06),
--   ``api_key``, ``api_endpoint`` (added 2025-08-24) were appended to the
--   CREATE statement in 05-public-tables.sql after the table had already
--   been created in the wild. CREATE TABLE IF NOT EXISTS preserves the
--   original schema on existing supabase-db-data volumes, so the columns
--   never land there — and llm-catalog-init's UPSERT (litellm/catalog-init/
--   scripts/sync-catalog.py) writes every one of them. Without this guard
--   a volume from before mid-2025 fails the UPSERT with
--   ``column "context_window" of relation "llms" does not exist``.
--
--   ADD COLUMN IF NOT EXISTS is a no-op on fresh installs (column already
--   present from the CREATE).
ALTER TABLE public.llms
    ADD COLUMN IF NOT EXISTS description text,
    ADD COLUMN IF NOT EXISTS size_gb numeric,
    ADD COLUMN IF NOT EXISTS context_window integer,
    ADD COLUMN IF NOT EXISTS api_key text,
    ADD COLUMN IF NOT EXISTS api_endpoint text;

-- 4. Convert legacy boolean capability columns to integer.
--   The original ``vision``/``content``/``structured_content``/``embeddings``
--   columns were ``boolean not null default false`` — pure on/off flags.
--   The current shape is ``integer not null default 0`` — a 0-N confidence
--   gradient consumed by hermes / litellm routing.
--
--   CREATE TABLE IF NOT EXISTS preserves the legacy boolean shape on
--   existing volumes; catalog-init then UPSERTs values like
--   ``content=8, structured_content=5`` and Postgres rejects the implicit
--   integer→boolean cast at write time.
--
--   The conversion is guarded by an information_schema check (idempotent —
--   skips when the column is already integer). ``CASE WHEN col THEN 1 ELSE 0
--   END`` preserves the legacy on/off semantics; old true rows become 1,
--   old false rows become 0 — compatible with the new gradient since 0/1
--   are valid integer values catalog-init reuses for "off / minimal".
DO $$
DECLARE
    col text;
BEGIN
    FOREACH col IN ARRAY ARRAY['vision', 'content', 'structured_content', 'embeddings']
    LOOP
        IF EXISTS (
            SELECT 1 FROM information_schema.columns
             WHERE table_schema = 'public'
               AND table_name = 'llms'
               AND column_name = col
               AND data_type = 'boolean'
        ) THEN
            EXECUTE format(
                'ALTER TABLE public.llms ALTER COLUMN %I DROP DEFAULT',
                col
            );
            EXECUTE format(
                'ALTER TABLE public.llms ALTER COLUMN %I TYPE integer USING (CASE WHEN %I THEN 1 ELSE 0 END)',
                col, col
            );
            EXECUTE format(
                'ALTER TABLE public.llms ALTER COLUMN %I SET DEFAULT 0',
                col
            );
            EXECUTE format(
                'ALTER TABLE public.llms ALTER COLUMN %I SET NOT NULL',
                col
            );
            RAISE NOTICE 'public.llms.% converted boolean → integer (legacy volume)', col;
        END IF;
    END LOOP;
END $$;

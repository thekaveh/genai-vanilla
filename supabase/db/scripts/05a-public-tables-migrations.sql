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

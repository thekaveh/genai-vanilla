-- 10a-langmem-migrations.sql
-- Idempotent migrations on top of 10-langmem-tables.sql.
--
-- Runs alphabetically after 10- and before 11- (cloud-providers seeding),
-- so the corrected column types are in place before anything queries the
-- memory_* tables.
--
-- Why this exists:
--   Commit 6e33a48 (2026-04-27) changed user_id on memory_facts,
--   memory_sessions, and memory_consolidation_log from
--   ``VARCHAR(255) REFERENCES public."user"(id)`` →
--   ``UUID REFERENCES public.users(id)``.
--
--   CREATE TABLE IF NOT EXISTS in 10-langmem-tables.sql preserves the
--   legacy shape on any supabase-db-data volume created between
--   2026-04-15 (commit ab2baf9 that first added the tables) and
--   2026-04-27 — the column stays VARCHAR and the FK still points at
--   ``public."user"`` (an Open WebUI legacy table that no longer exists
--   in this database). Every memory write from
--   services/backend/app/app/memory_store.py::_to_uuid passes an
--   asyncpg.UUID into the VARCHAR column and the FK violation surfaces
--   on the next INSERT — silently breaking every memory/extract,
--   memory/recall, and memory/consolidate request.
--
-- This migration is safe to re-run on existing DBs.

DO $$
DECLARE
    tbl text;
    legacy_fk text;
BEGIN
    FOREACH tbl IN ARRAY ARRAY[
        'memory_facts',
        'memory_sessions',
        'memory_consolidation_log'
    ]
    LOOP
        -- Skip if user_id is already uuid (fresh installs and post-migration runs).
        IF NOT EXISTS (
            SELECT 1 FROM information_schema.columns
             WHERE table_schema = 'public'
               AND table_name = tbl
               AND column_name = 'user_id'
               AND data_type = 'character varying'
        ) THEN
            CONTINUE;
        END IF;

        -- Drop the dangling FK to public."user" (the table no longer
        -- exists in supabase-db; Open WebUI's user table was renamed/
        -- relocated and the legacy reference now traps the column at the
        -- ALTER step below). conname is implementation-defined; resolve
        -- via pg_constraint with table scope so an unrelated FK with a
        -- similar name can't make this guard skip.
        SELECT conname
          INTO legacy_fk
          FROM pg_constraint
         WHERE conrelid = ('public.' || tbl)::regclass
           AND contype = 'f'
           AND array_length(conkey, 1) = 1
           AND (SELECT attname FROM pg_attribute
                 WHERE attrelid = conrelid
                   AND attnum  = conkey[1]) = 'user_id';
        IF legacy_fk IS NOT NULL THEN
            EXECUTE format('ALTER TABLE public.%I DROP CONSTRAINT %I', tbl, legacy_fk);
            RAISE NOTICE 'public.%: dropped legacy user_id FK %', tbl, legacy_fk;
        END IF;

        -- Convert VARCHAR(255) → UUID. If any row holds a non-UUID
        -- string the cast will fail loudly — the table is at most one
        -- 12-day window of fact data (commits ab2baf9 → 6e33a48) and a
        -- hard failure here points the operator at the exact rows to
        -- TRUNCATE rather than silently dropping data.
        EXECUTE format(
            'ALTER TABLE public.%I ALTER COLUMN user_id TYPE uuid USING user_id::uuid',
            tbl
        );

        -- Re-attach the FK to the canonical public.users table.
        EXECUTE format(
            'ALTER TABLE public.%I ADD CONSTRAINT %I FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE',
            tbl, tbl || '_user_id_fkey'
        );

        RAISE NOTICE 'public.%: user_id migrated VARCHAR(255) → UUID, FK → public.users(id)', tbl;
    END LOOP;
END $$;

-- 12-extend-comfyui-models.sql
-- Extend public.comfyui_models with the richer catalog metadata the new
-- comfyui-catalog-init pipeline (services/comfyui/catalog-init/scripts/sync-catalog.py)
-- populates from bootstrapper/utils/comfyui_library.py. Mirrors the LLM
-- side: schema lives in SQL, rows land via the init container's UPSERT.
--
-- Idempotent: every column uses IF NOT EXISTS so re-runs are safe.
-- The existing UNIQUE (name, type) constraint in 05-public-tables.sql
-- is the conflict target the sync script uses for ON CONFLICT.

DO $$ BEGIN
  ALTER TABLE public.comfyui_models
    ADD COLUMN IF NOT EXISTS family TEXT,
    ADD COLUMN IF NOT EXISTS sha256 TEXT,
    ADD COLUMN IF NOT EXISTS target_dir TEXT,
    ADD COLUMN IF NOT EXISTS min_vram_gb DECIMAL(5,2),
    ADD COLUMN IF NOT EXISTS cpu_supported BOOLEAN DEFAULT true,
    ADD COLUMN IF NOT EXISTS requires_custom_node JSONB DEFAULT '[]'::jsonb,
    ADD COLUMN IF NOT EXISTS popularity INTEGER DEFAULT 0,
    ADD COLUMN IF NOT EXISTS source TEXT;
END $$;

-- Index for the catalog-init activation UPDATE (`WHERE source = 'custom'`)
-- and for backend listing routes that filter by source provenance.
CREATE INDEX IF NOT EXISTS idx_comfyui_models_source ON public.comfyui_models(source);

-- 15-decommission-llms.sql
-- OWNER: litellm — decommission of the former public.llms catalog table.
--
-- The LLM model source-of-truth moved out of Postgres into per-service YAML
-- (services/ollama/models.yaml + services/litellm/models.yaml), resolved by
-- bootstrapper/utils/model_resolver.py. No service reads or writes public.llms
-- anymore (litellm-init renders config.yaml from the YAML; ollama-pull reads
-- OLLAMA_USER_MODELS/CUSTOM; weaviate/LDR/backend use LITELLM_*_MODEL env vars;
-- the n8n research workflow uses LITELLM_DEFAULT_MODEL).
--
-- Fresh installs never create public.llms (the former 11-litellm.sql is gone).
-- This drop cleans up pre-existing supabase-db-data volumes. Idempotent: a
-- no-op when the table is absent. The table held only the regenerable model
-- catalog (no precious user data — selections live in .env / the YAML), so the
-- drop is safe. DROP TABLE removes the table's own updated_at trigger; the
-- shared public.update_updated_at_column() function (07-functions.sql) is left
-- intact (still used by the research + memory triggers).

DROP TABLE IF EXISTS public.llms;

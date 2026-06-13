-- 08-seed-data.sql
-- Insert initial data into custom tables.
--
-- LLM catalog rows (Ollama, OpenAI, Anthropic, OpenRouter) are NOT
-- seeded here. ``llm-catalog-init`` is the single source of truth — it
-- UPSERTs every catalog row from ``bootstrapper/utils/llm_catalog.py``
-- on every ``docker compose up``, before any consumer queries
-- ``public.llms`` (compose ``depends_on: service_completed_successfully``
-- ordering — see the litellm-init, ollama-pull, and backend service
-- blocks in docker-compose.yml).
--
-- Removing the previous in-SQL Ollama seed (qwen3.6:latest,
-- qwen3-embedding:0.6b, nomic-embed-text) eliminates the drift hazard
-- where a Python catalog edit had to be mirrored here by hand. The
-- ``default_active`` flag on those entries in OLLAMA_DEFAULT_CATALOG
-- now drives their ``active=true`` state.

-- ComfyUI model rows are NOT seeded here. ``comfyui-catalog-init``
-- (services/comfyui/catalog-init/scripts/sync-catalog.py) is the single
-- source of truth — it UPSERTs every catalog row from
-- bootstrapper/utils/comfyui_library.py on every ``docker compose up``,
-- before comfyui-init queries ``public.comfyui_models`` for the active
-- download set. Mirrors the Ollama/LLM pipeline. The four previously
-- hardcoded rows (sd_v1-5_pruned_emaonly, sdxl_base_1.0,
-- vae_ft_mse_840000_ema_pruned, sdxl_vae) now arrive via the curated +
-- fallback layers of comfyui_library.

-- Insert some basic default workflows
DO $$ BEGIN
  IF NOT EXISTS (SELECT FROM public.comfyui_workflows WHERE name = 'Basic Text to Image') THEN
    INSERT INTO public.comfyui_workflows (name, description, workflow_data, category, active) VALUES
      ('Basic Text to Image', 'Simple text-to-image workflow using SD1.5', 
       '{"nodes": [{"id": 1, "type": "CheckpointLoaderSimple", "inputs": {"ckpt_name": "v1-5-pruned-emaonly.safetensors"}}, {"id": 2, "type": "CLIPTextEncode", "inputs": {"text": "a beautiful landscape", "clip": [1, 1]}}, {"id": 3, "type": "CLIPTextEncode", "inputs": {"text": "bad quality, blurry", "clip": [1, 1]}}, {"id": 4, "type": "KSampler", "inputs": {"seed": 42, "steps": 20, "cfg": 7.0, "sampler_name": "euler", "scheduler": "normal", "model": [1, 0], "positive": [2, 0], "negative": [3, 0]}}, {"id": 5, "type": "VAEDecode", "inputs": {"samples": [4, 0], "vae": [1, 2]}}, {"id": 6, "type": "SaveImage", "inputs": {"filename_prefix": "ComfyUI", "images": [5, 0]}}]}', 
       'basic', true);
  END IF;
END $$;

DO $$ BEGIN
  IF NOT EXISTS (SELECT FROM public.comfyui_workflows WHERE name = 'SDXL Text to Image') THEN
    INSERT INTO public.comfyui_workflows (name, description, workflow_data, category, active) VALUES
      ('SDXL Text to Image', 'High-quality text-to-image workflow using SDXL', 
       '{"nodes": [{"id": 1, "type": "CheckpointLoaderSimple", "inputs": {"ckpt_name": "sd_xl_base_1.0.safetensors"}}, {"id": 2, "type": "CLIPTextEncode", "inputs": {"text": "a beautiful landscape", "clip": [1, 1]}}, {"id": 3, "type": "CLIPTextEncode", "inputs": {"text": "bad quality, blurry", "clip": [1, 1]}}, {"id": 4, "type": "KSampler", "inputs": {"seed": 42, "steps": 25, "cfg": 7.5, "sampler_name": "dpmpp_2m", "scheduler": "karras", "model": [1, 0], "positive": [2, 0], "negative": [3, 0]}}, {"id": 5, "type": "VAEDecode", "inputs": {"samples": [4, 0], "vae": [1, 2]}}, {"id": 6, "type": "SaveImage", "inputs": {"filename_prefix": "ComfyUI_SDXL", "images": [5, 0]}}]}', 
       'basic', true);
  END IF;
END $$;

-- Add any other seed data here

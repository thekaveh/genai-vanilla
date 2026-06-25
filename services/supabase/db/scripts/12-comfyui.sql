-- 12-comfyui.sql
-- OWNER: comfyui — comfyui_models / comfyui_workflows / comfyui_generations,
-- their indexes, the catalog-metadata extension columns, and the default
-- workflow seeds. Only this service's objects belong here.
-- Assembled verbatim from the former 05-public-tables.sql (comfyui tables +
-- indexes), 12-extend-comfyui-models.sql (extension columns + source index),
-- and 08-seed-data.sql (default workflow seeds). Tables are created before the
-- ALTER/seed blocks that depend on them.

CREATE TABLE IF NOT EXISTS public.comfyui_models (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    type VARCHAR(50) NOT NULL, -- 'checkpoint', 'vae', 'lora', 'controlnet', 'upscaler', 'embeddings'
    filename VARCHAR(255) NOT NULL,
    download_url TEXT NOT NULL,
    file_size_gb DECIMAL(5,2),
    description TEXT,
    active BOOLEAN DEFAULT true,
    essential BOOLEAN DEFAULT false, -- Models that should be downloaded by default
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    CONSTRAINT unique_comfyui_model_name UNIQUE (name, type)
);

CREATE INDEX IF NOT EXISTS idx_comfyui_models_active ON public.comfyui_models(active);
CREATE INDEX IF NOT EXISTS idx_comfyui_models_essential ON public.comfyui_models(essential);
CREATE INDEX IF NOT EXISTS idx_comfyui_models_type ON public.comfyui_models(type);

CREATE TABLE IF NOT EXISTS public.comfyui_workflows (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    description TEXT,
    workflow_data JSONB NOT NULL,
    category VARCHAR(100) DEFAULT 'custom',
    active BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    CONSTRAINT unique_comfyui_workflow_name UNIQUE (name)
);

CREATE INDEX IF NOT EXISTS idx_comfyui_workflows_active ON public.comfyui_workflows(active);
CREATE INDEX IF NOT EXISTS idx_comfyui_workflows_category ON public.comfyui_workflows(category);

CREATE TABLE IF NOT EXISTS public.comfyui_generations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    prompt TEXT NOT NULL,
    negative_prompt TEXT,
    workflow_id UUID REFERENCES public.comfyui_workflows(id),
    image_url TEXT,
    image_path TEXT,
    parameters JSONB, -- Store generation parameters like seed, steps, cfg, etc.
    status VARCHAR(50) DEFAULT 'pending', -- 'pending', 'processing', 'completed', 'failed'
    error_message TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    completed_at TIMESTAMP WITH TIME ZONE
);

CREATE INDEX IF NOT EXISTS idx_comfyui_generations_status ON public.comfyui_generations(status);
CREATE INDEX IF NOT EXISTS idx_comfyui_generations_created_at ON public.comfyui_generations(created_at DESC);

-- Catalog-metadata extension columns (formerly 12-extend-comfyui-models.sql).
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

CREATE INDEX IF NOT EXISTS idx_comfyui_models_source ON public.comfyui_models(source);

-- Default workflow seeds (formerly 08-seed-data.sql).
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

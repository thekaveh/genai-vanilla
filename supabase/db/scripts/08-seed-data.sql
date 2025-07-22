-- 08-seed-data.sql
-- Insert initial data into custom tables

-- Insert default Ollama models (safe to re-run)
DO $$ BEGIN
  IF NOT EXISTS (SELECT FROM public.llms WHERE name = 'mxbai-embed-large' AND provider = 'ollama') THEN
    INSERT INTO public.llms (name, provider, active, embeddings, content) VALUES
      ('mxbai-embed-large', 'ollama', true, true, false);
  END IF;
END $$;

-- Insert qwen3:latest as default content LLM for Local Deep Researcher
DO $$ BEGIN
  IF NOT EXISTS (SELECT FROM public.llms WHERE name = 'qwen3:latest' AND provider = 'ollama') THEN
    INSERT INTO public.llms (name, provider, active, embeddings, content, description, size_gb, context_window) VALUES
      ('qwen3:latest', 'ollama', true, false, true, 'Latest generation LLM with 100+ language support and strong reasoning capabilities', 5.2, 40000);
  END IF;
END $$;

-- Insert essential ComfyUI models (safe to re-run)
-- Note: These are popular, freely available models. Users should verify licensing for their use case.

-- Stable Diffusion 1.5 - Essential checkpoint
DO $$ BEGIN
  IF NOT EXISTS (SELECT FROM public.comfyui_models WHERE name = 'sd_v1-5_pruned_emaonly' AND type = 'checkpoint') THEN
    INSERT INTO public.comfyui_models (name, type, filename, download_url, file_size_gb, description, active, essential) VALUES
      ('sd_v1-5_pruned_emaonly', 'checkpoint', 'sd_v1-5_pruned_emaonly.safetensors', 'https://huggingface.co/runwayml/stable-diffusion-v1-5/resolve/main/v1-5-pruned-emaonly.safetensors', 3.97, 'Stable Diffusion 1.5 - Essential base model for general image generation', true, true);
  END IF;
END $$;

-- SDXL Base - Modern checkpoint
DO $$ BEGIN
  IF NOT EXISTS (SELECT FROM public.comfyui_models WHERE name = 'sdxl_base_1.0' AND type = 'checkpoint') THEN
    INSERT INTO public.comfyui_models (name, type, filename, download_url, file_size_gb, description, active, essential) VALUES
      ('sdxl_base_1.0', 'checkpoint', 'sdxl_base_1.0.safetensors', 'https://huggingface.co/stabilityai/stable-diffusion-xl-base-1.0/resolve/main/sd_xl_base_1.0.safetensors', 6.94, 'SDXL Base 1.0 - High-quality image generation with better prompt adherence', true, true);
  END IF;
END $$;

-- VAE Models - Essential for proper image decoding
DO $$ BEGIN
  IF NOT EXISTS (SELECT FROM public.comfyui_models WHERE name = 'vae_ft_mse_840000_ema_pruned' AND type = 'vae') THEN
    INSERT INTO public.comfyui_models (name, type, filename, download_url, file_size_gb, description, active, essential) VALUES
      ('vae_ft_mse_840000_ema_pruned', 'vae', 'vae-ft-mse-840000-ema-pruned.safetensors', 'https://huggingface.co/stabilityai/sd-vae-ft-mse-original/resolve/main/vae-ft-mse-840000-ema-pruned.safetensors', 0.32, 'Standard VAE for Stable Diffusion 1.5 - Improves image quality and color accuracy', true, true);
  END IF;
END $$;

DO $$ BEGIN
  IF NOT EXISTS (SELECT FROM public.comfyui_models WHERE name = 'sdxl_vae' AND type = 'vae') THEN
    INSERT INTO public.comfyui_models (name, type, filename, download_url, file_size_gb, description, active, essential) VALUES
      ('sdxl_vae', 'vae', 'sdxl_vae.safetensors', 'https://huggingface.co/stabilityai/sdxl-vae/resolve/main/sdxl_vae.safetensors', 0.32, 'SDXL VAE - Required for SDXL models to produce proper images', true, true);
  END IF;
END $$;

-- Insert some basic default workflows
DO $$ BEGIN
  IF NOT EXISTS (SELECT FROM public.comfyui_workflows WHERE name = 'Basic Text to Image') THEN
    INSERT INTO public.comfyui_workflows (name, description, workflow_data, category, active) VALUES
      ('Basic Text to Image', 'Simple text-to-image workflow using SD1.5', 
       '{"nodes": [{"id": 1, "type": "CheckpointLoaderSimple", "inputs": {"ckpt_name": "sd_v1-5_pruned_emaonly.safetensors"}}, {"id": 2, "type": "CLIPTextEncode", "inputs": {"text": "a beautiful landscape", "clip": [1, 1]}}, {"id": 3, "type": "CLIPTextEncode", "inputs": {"text": "bad quality, blurry", "clip": [1, 1]}}, {"id": 4, "type": "KSampler", "inputs": {"seed": 42, "steps": 20, "cfg": 7.0, "sampler_name": "euler", "scheduler": "normal", "model": [1, 0], "positive": [2, 0], "negative": [3, 0]}}, {"id": 5, "type": "VAEDecode", "inputs": {"samples": [4, 0], "vae": [1, 2]}}, {"id": 6, "type": "SaveImage", "inputs": {"filename_prefix": "ComfyUI", "images": [5, 0]}}]}', 
       'basic', true);
  END IF;
END $$;

DO $$ BEGIN
  IF NOT EXISTS (SELECT FROM public.comfyui_workflows WHERE name = 'SDXL Text to Image') THEN
    INSERT INTO public.comfyui_workflows (name, description, workflow_data, category, active) VALUES
      ('SDXL Text to Image', 'High-quality text-to-image workflow using SDXL', 
       '{"nodes": [{"id": 1, "type": "CheckpointLoaderSimple", "inputs": {"ckpt_name": "sdxl_base_1.0.safetensors"}}, {"id": 2, "type": "CLIPTextEncode", "inputs": {"text": "a beautiful landscape", "clip": [1, 1]}}, {"id": 3, "type": "CLIPTextEncode", "inputs": {"text": "bad quality, blurry", "clip": [1, 1]}}, {"id": 4, "type": "KSampler", "inputs": {"seed": 42, "steps": 25, "cfg": 7.5, "sampler_name": "dpmpp_2m", "scheduler": "karras", "model": [1, 0], "positive": [2, 0], "negative": [3, 0]}}, {"id": 5, "type": "VAEDecode", "inputs": {"samples": [4, 0], "vae": [1, 2]}}, {"id": 6, "type": "SaveImage", "inputs": {"filename_prefix": "ComfyUI_SDXL", "images": [5, 0]}}]}', 
       'basic', true);
  END IF;
END $$;

-- Add any other seed data here

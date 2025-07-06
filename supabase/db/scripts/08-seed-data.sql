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

-- Add any other seed data here

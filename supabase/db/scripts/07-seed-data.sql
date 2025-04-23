-- 07-seed-data.sql
-- Insert initial data into custom tables

-- Insert default Ollama models (safe to re-run)
DO $$ BEGIN
  IF NOT EXISTS (SELECT FROM public.llms WHERE name = 'mxbai-embed-large' AND provider = 'ollama') THEN
    INSERT INTO public.llms (name, provider, active, embeddings, content) VALUES
      ('mxbai-embed-large', 'ollama', true, true, false);
  END IF;
END $$;

-- Add any other seed data here

-- 04-storage.sql
-- Configure storage schema tables, policies, and create default bucket

-- Create storage.buckets table
CREATE TABLE IF NOT EXISTS storage.buckets (
    id text primary key,
    name text not null,
    owner uuid references auth.users,
    created_at timestamptz default now(),
    updated_at timestamptz default now(),
    file_size_limit bigint,
    allowed_mime_types text[],
    avif_autodetection boolean default false
);

-- Create storage.objects table
DO $$ BEGIN
    -- Drop the table if it exists to ensure clean recreation
    DROP TABLE IF EXISTS storage.objects;
    
    -- Create the table with all columns including the generated column
    CREATE TABLE storage.objects (
        id uuid primary key default gen_random_uuid(),
        bucket_id text references storage.buckets(id),
        name text,
        owner uuid references auth.users,
        created_at timestamptz default now(),
        updated_at timestamptz default now(),
        last_accessed_at timestamptz default now(),
        metadata jsonb,
        path_tokens text[] generated always as (string_to_array(name, '/')) stored
    );
END $$;

-- Create indexes
CREATE INDEX IF NOT EXISTS bname ON storage.buckets (name);
CREATE INDEX IF NOT EXISTS owner ON storage.buckets (owner);
CREATE INDEX IF NOT EXISTS bucket_id ON storage.objects (bucket_id);
CREATE INDEX IF NOT EXISTS name ON storage.objects (name);
CREATE INDEX IF NOT EXISTS owner ON storage.objects (owner);
CREATE INDEX IF NOT EXISTS path_tokens_idx ON storage.objects USING gin (path_tokens);

-- Disable RLS since we're managing access through GRANTs
ALTER TABLE storage.buckets DISABLE ROW LEVEL SECURITY;
ALTER TABLE storage.objects DISABLE ROW LEVEL SECURITY;


-- Grant privileges to roles
GRANT ALL ON storage.buckets TO service_role;
GRANT ALL ON storage.objects TO service_role;
GRANT ALL ON ALL SEQUENCES IN SCHEMA storage TO service_role;

GRANT SELECT ON storage.buckets TO anon, authenticated;
GRANT SELECT ON storage.objects TO anon, authenticated;
GRANT INSERT, UPDATE, DELETE ON storage.objects TO authenticated;

-- Create default storage bucket (safe to re-run)
DO $$ BEGIN
  IF EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'authenticated') THEN
    INSERT INTO storage.buckets (id, name)
    VALUES ('default', 'default')
    ON CONFLICT (id) DO NOTHING;
  END IF;
END $$;

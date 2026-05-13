-- 06-functions.sql
-- Create custom functions

-- Create health check function (safe to re-run)
CREATE OR REPLACE FUNCTION public.health() RETURNS text AS $$
BEGIN
  RETURN 'healthy';
END;
$$ LANGUAGE plpgsql;

-- Grant access to the health function (safe to re-run)
DO $$
BEGIN
  IF EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'anon') THEN
    GRANT EXECUTE ON FUNCTION public.health() TO anon;
  END IF;
END
$$;

-- Create updated_at trigger function (safe to re-run)
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Create updated_at trigger for llms table
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_trigger 
        WHERE tgname = 'update_llms_updated_at'
    ) THEN
        CREATE TRIGGER update_llms_updated_at 
            BEFORE UPDATE ON public.llms 
            FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
    END IF;
END $$;

-- Add any other custom functions here

-- Enable logical replication for Realtime
DO $$
BEGIN
  -- Check if wal_level is not already logical
  IF current_setting('wal_level') != 'logical' THEN
    ALTER SYSTEM SET wal_level = 'logical';
    -- Note: This requires a database restart to take effect
  END IF;
END $$;

-- Create replication slot for realtime if it doesn't exist
SELECT pg_create_logical_replication_slot('supabase_realtime_slot', 'pgoutput')
WHERE NOT EXISTS (
  SELECT 1 FROM pg_replication_slots 
  WHERE slot_name = 'supabase_realtime_slot'
);

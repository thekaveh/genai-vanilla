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

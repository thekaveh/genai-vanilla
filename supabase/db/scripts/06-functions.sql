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

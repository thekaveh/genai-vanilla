-- Create auth schema if it does not exist
DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_namespace WHERE nspname = 'auth'
  ) THEN
    EXECUTE 'CREATE SCHEMA auth';
  END IF;
END
$$;

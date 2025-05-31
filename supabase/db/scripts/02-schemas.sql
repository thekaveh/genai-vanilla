-- 02-schemas.sql

CREATE SCHEMA IF NOT EXISTS auth;
CREATE SCHEMA IF NOT EXISTS storage;

-- CREATE SCHEMA IF NOT EXISTS openwebui;
-- GRANT ALL PRIVILEGES ON SCHEMA openwebui TO supabase_admin;

CREATE SCHEMA IF NOT EXISTS n8n;
GRANT ALL PRIVILEGES ON SCHEMA n8n TO supabase_admin;

CREATE SCHEMA IF NOT EXISTS realtime;
GRANT USAGE ON SCHEMA realtime TO postgres, anon, authenticated, service_role;
ALTER DEFAULT PRIVILEGES IN SCHEMA realtime GRANT ALL ON TABLES TO postgres, anon, authenticated, service_role;
ALTER DEFAULT PRIVILEGES IN SCHEMA realtime GRANT ALL ON FUNCTIONS TO postgres, anon, authenticated, service_role;
ALTER DEFAULT PRIVILEGES IN SCHEMA realtime GRANT ALL ON SEQUENCES TO postgres, anon, authenticated, service_role;

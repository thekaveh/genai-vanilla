-- 01-extensions.sql
-- Enable necessary extensions

CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS postgis;

-- Required for logical replication used by Realtime
CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- Add any other required extensions here

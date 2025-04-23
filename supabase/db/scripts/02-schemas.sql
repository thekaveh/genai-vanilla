-- 02-schemas.sql
-- Ensure required schemas exist

-- Base Supabase image should create these, but ensure they exist just in case.
CREATE SCHEMA IF NOT EXISTS auth;
CREATE SCHEMA IF NOT EXISTS storage;

-- Add any other custom schemas here if needed
-- CREATE SCHEMA IF NOT EXISTS my_custom_schema;

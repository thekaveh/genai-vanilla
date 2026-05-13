-- 03-auth-types.sql
-- Create custom auth types needed by GoTrue

-- Create type for factor_type if it doesn't exist
DO $$ BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_type t
        JOIN pg_namespace n ON t.typnamespace = n.oid
        WHERE t.typname = 'factor_type' AND n.nspname = 'auth'
    ) THEN
        CREATE TYPE auth.factor_type AS ENUM ('totp', 'webauthn');
    END IF;
EXCEPTION
    WHEN duplicate_object THEN
        RAISE NOTICE 'Type auth.factor_type already exists, skipping creation.';
END $$;

-- Add 'phone' value if the type exists and the value doesn't
DO $$ BEGIN
    IF EXISTS (
        SELECT 1 FROM pg_type t
        JOIN pg_namespace n ON t.typnamespace = n.oid
        WHERE t.typname = 'factor_type' AND n.nspname = 'auth'
    ) THEN
        ALTER TYPE auth.factor_type ADD VALUE IF NOT EXISTS 'phone';
    ELSE
        RAISE WARNING 'Type auth.factor_type does not exist, cannot add value ''phone''.';
    END IF;
EXCEPTION
    WHEN duplicate_object THEN -- Ignore if value already exists
        RAISE NOTICE 'Value ''phone'' already exists in type auth.factor_type.';
END $$;

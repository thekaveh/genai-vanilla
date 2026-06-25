-- 10-users.sql
-- OWNER: backend/auth — public.users. FK-referenced by the research (13) and
-- memory (14) slices, so this MUST sort before them. Only this service's
-- objects belong here. Moved verbatim from the former 05-public-tables.sql.

CREATE TABLE IF NOT EXISTS public.users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT now()
);

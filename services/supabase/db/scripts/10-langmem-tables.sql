-- 10-langmem-tables.sql
-- Memory service tables for LangMem integration
-- Provides persistent conversation memory with fact extraction, recall, and consolidation

-- Core memory facts table - stores extracted facts from conversations
CREATE TABLE IF NOT EXISTS public.memory_facts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES public.users(id) ON DELETE CASCADE,
    namespace VARCHAR(100) NOT NULL DEFAULT 'default',
    content TEXT NOT NULL,
    fact_type VARCHAR(50) NOT NULL DEFAULT 'observation'
        CHECK (fact_type IN ('observation', 'preference', 'instruction', 'relationship', 'event')),
    confidence FLOAT DEFAULT 1.0 CHECK (confidence >= 0.0 AND confidence <= 1.0),
    source_conversation_id UUID,
    source_message_ids JSONB DEFAULT '[]'::jsonb,
    metadata JSONB DEFAULT '{}'::jsonb,
    embedding vector(768),                -- pgvector fallback column (used when Weaviate unavailable)
    weaviate_id VARCHAR(255),             -- Weaviate vector reference (used when Weaviate available)
    is_active BOOLEAN DEFAULT true,
    superseded_by UUID REFERENCES public.memory_facts(id),
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now(),
    expires_at TIMESTAMPTZ
);

-- Memory extraction sessions - tracks conversation-to-memory processing
CREATE TABLE IF NOT EXISTS public.memory_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES public.users(id) ON DELETE CASCADE,
    conversation_id UUID,
    status VARCHAR(20) NOT NULL DEFAULT 'pending'
        CHECK (status IN ('pending', 'running', 'completed', 'failed')),
    facts_extracted INTEGER DEFAULT 0,
    facts_consolidated INTEGER DEFAULT 0,
    processing_started_at TIMESTAMPTZ,
    processing_completed_at TIMESTAMPTZ,
    error_message TEXT,
    created_at TIMESTAMPTZ DEFAULT now()
);

-- Memory consolidation audit log - tracks merge/update/supersede operations
CREATE TABLE IF NOT EXISTS public.memory_consolidation_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES public.users(id) ON DELETE CASCADE,
    action VARCHAR(50) NOT NULL
        CHECK (action IN ('merged', 'updated', 'superseded', 'expired')),
    source_fact_ids UUID[] NOT NULL,
    result_fact_id UUID REFERENCES public.memory_facts(id),
    reason TEXT,
    created_at TIMESTAMPTZ DEFAULT now()
);

-- Create indexes for better query performance
CREATE INDEX IF NOT EXISTS idx_memory_facts_user_id ON public.memory_facts(user_id);
CREATE INDEX IF NOT EXISTS idx_memory_facts_namespace ON public.memory_facts(namespace);
CREATE INDEX IF NOT EXISTS idx_memory_facts_type ON public.memory_facts(fact_type);
CREATE INDEX IF NOT EXISTS idx_memory_facts_active ON public.memory_facts(is_active);
CREATE INDEX IF NOT EXISTS idx_memory_facts_created_at ON public.memory_facts(created_at);
CREATE INDEX IF NOT EXISTS idx_memory_facts_user_active ON public.memory_facts(user_id, is_active);
CREATE INDEX IF NOT EXISTS idx_memory_facts_conversation ON public.memory_facts(source_conversation_id);
CREATE INDEX IF NOT EXISTS idx_memory_sessions_user_id ON public.memory_sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_memory_sessions_conversation ON public.memory_sessions(conversation_id);
CREATE INDEX IF NOT EXISTS idx_memory_sessions_status ON public.memory_sessions(status);
CREATE INDEX IF NOT EXISTS idx_memory_consolidation_user_id ON public.memory_consolidation_log(user_id);

-- pgvector index for embedding similarity search (HNSW for approximate nearest neighbor)
-- HNSW is preferred over IVFFlat because it works correctly on empty/small tables
CREATE INDEX IF NOT EXISTS idx_memory_facts_embedding ON public.memory_facts
    USING hnsw (embedding vector_cosine_ops);

-- Apply updated_at trigger (reusing function from 09-research-tables.sql)
DROP TRIGGER IF EXISTS update_memory_facts_updated_at ON public.memory_facts;
CREATE TRIGGER update_memory_facts_updated_at
    BEFORE UPDATE ON public.memory_facts
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Enable Row Level Security
ALTER TABLE public.memory_facts ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.memory_sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.memory_consolidation_log ENABLE ROW LEVEL SECURITY;

-- Drop existing policies if they exist (idempotent)
DROP POLICY IF EXISTS "Users can view their own memory facts" ON public.memory_facts;
DROP POLICY IF EXISTS "Service role can access all memory facts" ON public.memory_facts;
DROP POLICY IF EXISTS "Users can view their own memory sessions" ON public.memory_sessions;
DROP POLICY IF EXISTS "Service role can access all memory sessions" ON public.memory_sessions;
DROP POLICY IF EXISTS "Users can view their own consolidation logs" ON public.memory_consolidation_log;
DROP POLICY IF EXISTS "Service role can access all consolidation logs" ON public.memory_consolidation_log;

-- Service role (backend) can access all memory data
CREATE POLICY "Service role can access all memory facts" ON public.memory_facts
    FOR ALL USING (true);

CREATE POLICY "Service role can access all memory sessions" ON public.memory_sessions
    FOR ALL USING (true);

CREATE POLICY "Service role can access all consolidation logs" ON public.memory_consolidation_log
    FOR ALL USING (true);

-- Grant permissions to service roles
GRANT ALL ON public.memory_facts TO service_role;
GRANT ALL ON public.memory_sessions TO service_role;
GRANT ALL ON public.memory_consolidation_log TO service_role;

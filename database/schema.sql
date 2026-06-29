-- ================================================
-- FinSight Enterprise AI — Supabase Schema
-- ================================================

-- 1. DOCUMENTS TABLE
-- Stores metadata for every file ingested into the system
CREATE TABLE IF NOT EXISTS documents (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    file_name TEXT NOT NULL,
    file_type TEXT NOT NULL,          -- 'bank_statement', 'invoice', 'report'
    file_path TEXT,                    -- path in Supabase Storage
    status TEXT DEFAULT 'pending',     -- 'pending', 'processing', 'completed', 'failed'
    uploaded_at TIMESTAMPTZ DEFAULT NOW(),
    processed_at TIMESTAMPTZ,
    metadata JSONB DEFAULT '{}'        -- any extra info as JSON
);

-- 2. TRANSACTIONS TABLE
-- Stores individual financial transactions extracted from documents
CREATE TABLE IF NOT EXISTS transactions (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    document_id UUID REFERENCES documents(id) ON DELETE CASCADE,
    transaction_date DATE,
    description TEXT,
    amount NUMERIC(15, 2),
    currency TEXT DEFAULT 'AED',
    transaction_type TEXT,             -- 'credit', 'debit'
    category TEXT,                     -- 'salary', 'vendor', 'transfer' etc
    account_number TEXT,
    confidence_score NUMERIC(5, 4),    -- 0.0 to 1.0, how confident the LLM was
    is_flagged BOOLEAN DEFAULT FALSE,  -- flagged for human review
    flag_reason TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 3. EXTRACTION RESULTS TABLE
-- Stores the full structured output from the LLM extraction pipeline
CREATE TABLE IF NOT EXISTS extraction_results (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    document_id UUID REFERENCES documents(id) ON DELETE CASCADE,
    extracted_fields JSONB NOT NULL,   -- all fields the LLM extracted
    confidence_scores JSONB,           -- per-field confidence scores
    model_used TEXT,                   -- which LLM was used
    extraction_time_ms INTEGER,        -- how long extraction took
    tokens_used INTEGER,               -- token count for cost tracking
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 4. AUDIT LOGS TABLE
-- Records every agent decision — this is our governance layer
CREATE TABLE IF NOT EXISTS audit_logs (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    run_id TEXT NOT NULL,              -- unique ID for each agent run
    agent_name TEXT NOT NULL,          -- which agent made this entry
    action TEXT NOT NULL,              -- what the agent did
    input_summary TEXT,                -- brief summary of what went in
    output_summary TEXT,               -- brief summary of what came out
    decision TEXT,                     -- the actual decision made
    reasoning TEXT,                    -- why the agent made this decision
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 5. REVIEW QUEUE TABLE
-- Items flagged by agents that need human approval
CREATE TABLE IF NOT EXISTS review_queue (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    transaction_id UUID REFERENCES transactions(id) ON DELETE CASCADE,
    run_id TEXT NOT NULL,
    flag_reason TEXT NOT NULL,         -- why this was flagged
    risk_level TEXT DEFAULT 'medium',  -- 'low', 'medium', 'high'
    status TEXT DEFAULT 'pending',     -- 'pending', 'approved', 'rejected'
    reviewer_notes TEXT,               -- human reviewer's comments
    reviewed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 6. RUN METRICS TABLE
-- Tracks performance and cost of every agent run
CREATE TABLE IF NOT EXISTS run_metrics (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    run_id TEXT NOT NULL,
    total_tokens INTEGER DEFAULT 0,
    total_cost_usd NUMERIC(10, 6) DEFAULT 0,
    latency_ms INTEGER,
    agents_involved TEXT[],            -- array of agent names used
    documents_processed INTEGER DEFAULT 0,
    transactions_extracted INTEGER DEFAULT 0,
    flags_raised INTEGER DEFAULT 0,
    status TEXT DEFAULT 'completed',   -- 'completed', 'failed', 'partial'
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ================================================
-- INDEXES — speeds up common queries
-- ================================================
CREATE INDEX IF NOT EXISTS idx_transactions_document_id ON transactions(document_id);
CREATE INDEX IF NOT EXISTS idx_transactions_is_flagged ON transactions(is_flagged);
CREATE INDEX IF NOT EXISTS idx_audit_logs_run_id ON audit_logs(run_id);
CREATE INDEX IF NOT EXISTS idx_review_queue_status ON review_queue(status);
CREATE INDEX IF NOT EXISTS idx_run_metrics_run_id ON run_metrics(run_id);
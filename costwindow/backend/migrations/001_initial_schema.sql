-- ============================================================
-- CostWindow — Initial Schema
-- Run in: Supabase Dashboard → SQL Editor → New Query
-- ============================================================

-- Users (public profile, links to Supabase auth.users)
CREATE TABLE public.users (
    id              UUID        PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    email           TEXT        UNIQUE NOT NULL,
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    stripe_customer_id TEXT,
    plan            TEXT        DEFAULT 'free' NOT NULL
);

-- CostWindow API keys (used by the Python SDK to authenticate ingestion)
CREATE TABLE public.api_keys (
    id              UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         UUID        NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
    key_hash        TEXT        NOT NULL UNIQUE,  -- SHA-256 of the plaintext key
    key_prefix      TEXT        NOT NULL,          -- first 16 chars shown in UI (e.g. "cw_live_abc123de")
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    last_used_at    TIMESTAMPTZ
);

-- Processes (named groups of API calls — e.g. "quesi-horoscope")
CREATE TABLE public.processes (
    id              UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         UUID        NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
    label           TEXT        NOT NULL,
    provider        TEXT        NOT NULL,           -- "anthropic", "openai", or "manual"
    description     TEXT,
    is_active       BOOLEAN     DEFAULT TRUE NOT NULL,
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(user_id, label)
);

-- API calls (one row per tracked AI call)
CREATE TABLE public.api_calls (
    id              UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    process_id      UUID        NOT NULL REFERENCES public.processes(id) ON DELETE CASCADE,
    user_id         UUID        NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
    model           TEXT        NOT NULL,           -- e.g. "claude-sonnet-4-6"
    input_tokens    INTEGER     NOT NULL DEFAULT 0,
    output_tokens   INTEGER     NOT NULL DEFAULT 0,
    cached_tokens   INTEGER     NOT NULL DEFAULT 0,
    cost_usd        NUMERIC(14, 8) NOT NULL DEFAULT 0,
    provider        TEXT        NOT NULL,
    called_at       TIMESTAMPTZ DEFAULT NOW(),
    is_manual       BOOLEAN     DEFAULT FALSE NOT NULL,
    metadata        JSONB
);

-- User settings (currency preference, spike threshold, alerts)
CREATE TABLE public.user_settings (
    user_id         UUID        PRIMARY KEY REFERENCES public.users(id) ON DELETE CASCADE,
    currency        TEXT        DEFAULT 'GBP' NOT NULL,
    spike_threshold NUMERIC     DEFAULT 2.0 NOT NULL,
    email_alerts    BOOLEAN     DEFAULT FALSE NOT NULL
);

-- ── Indexes ──────────────────────────────────────────────────
CREATE INDEX idx_api_calls_user_id     ON public.api_calls(user_id);
CREATE INDEX idx_api_calls_process_id  ON public.api_calls(process_id);
CREATE INDEX idx_api_calls_called_at   ON public.api_calls(called_at);
CREATE INDEX idx_api_calls_user_date   ON public.api_calls(user_id, called_at);
CREATE INDEX idx_processes_user_id     ON public.processes(user_id);
CREATE INDEX idx_api_keys_key_hash     ON public.api_keys(key_hash);

-- ── Row Level Security ────────────────────────────────────────
-- Enabled on all tables. The backend uses the service_role key which bypasses RLS.
-- This means the backend can read/write any row; the anon key cannot read anything.

ALTER TABLE public.users        ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.api_keys     ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.processes    ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.api_calls    ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.user_settings ENABLE ROW LEVEL SECURITY;

-- Service role bypasses RLS by default in Supabase — no explicit policy needed.
-- If you ever add Supabase Realtime or direct client queries, add user-scoped policies here.

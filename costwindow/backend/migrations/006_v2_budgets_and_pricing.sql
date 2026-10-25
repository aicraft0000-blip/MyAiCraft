-- v2: budgets wired to kill switch, cost-driver flag, balance reconciliation
-- See docs/SPEC-V2.md

ALTER TABLE public.processes ADD COLUMN IF NOT EXISTS budget_usd_month NUMERIC(10,2);
ALTER TABLE public.processes ADD COLUMN IF NOT EXISTS budget_action    TEXT NOT NULL DEFAULT 'warn';      -- 'warn' | 'block'
ALTER TABLE public.processes ADD COLUMN IF NOT EXISTS cost_driver      TEXT NOT NULL DEFAULT 'scheduled'; -- 'scheduled' | 'demand'
ALTER TABLE public.processes ADD COLUMN IF NOT EXISTS blocked_reason   TEXT;
ALTER TABLE public.processes ADD COLUMN IF NOT EXISTS blocked_at       TIMESTAMPTZ;

ALTER TABLE public.provider_balances ADD COLUMN IF NOT EXISTS user_id UUID REFERENCES public.users(id) ON DELETE CASCADE;
ALTER TABLE public.provider_balances ADD COLUMN IF NOT EXISTS source  TEXT NOT NULL DEFAULT 'manual';     -- 'manual' | 'admin_api'

-- Admin/usage-report keys for balance reconciliation (encrypted by the backend before insert)
CREATE TABLE IF NOT EXISTS public.provider_credentials (
  id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id     UUID NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
  provider    TEXT NOT NULL,
  credential  TEXT NOT NULL,
  created_at  TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE(user_id, provider)
);

-- Helpful index for month-to-date spend lookups in the ingest path
CREATE INDEX IF NOT EXISTS idx_api_calls_process_called_at
  ON public.api_calls (process_id, called_at);

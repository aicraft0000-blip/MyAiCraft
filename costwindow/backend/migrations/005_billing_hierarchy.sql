-- ============================================================
-- CostWindow — Billing Hierarchy
-- Adds billing_type and subscription_id to processes so the
-- dashboard can group tools under their billing parent:
--   billing_type='subscription' → included in a flat plan
--   billing_type='api'          → pay-per-token (default)
-- ============================================================

ALTER TABLE public.processes
  ADD COLUMN IF NOT EXISTS billing_type    TEXT NOT NULL DEFAULT 'api',
  ADD COLUMN IF NOT EXISTS subscription_id TEXT REFERENCES public.subscriptions(id) ON DELETE SET NULL;

CREATE INDEX IF NOT EXISTS idx_processes_subscription_id ON public.processes(subscription_id);

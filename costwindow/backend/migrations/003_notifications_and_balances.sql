-- Migration 003: notifications toggle + provider balances

ALTER TABLE user_settings
  ADD COLUMN IF NOT EXISTS notifications_enabled boolean DEFAULT true;

CREATE TABLE IF NOT EXISTS provider_balances (
  id           uuid DEFAULT gen_random_uuid() PRIMARY KEY,
  provider     text NOT NULL,
  balance_usd  numeric(10,4),
  used_usd     numeric(10,4),
  granted_usd  numeric(10,4),
  fetched_at   timestamptz DEFAULT now()
);

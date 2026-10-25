-- Migration 004: paying customers table for subscription gating

CREATE TABLE IF NOT EXISTS customers (
  id                     uuid DEFAULT gen_random_uuid() PRIMARY KEY,
  email                  text NOT NULL UNIQUE,
  stripe_customer_id     text,
  stripe_subscription_id text,
  plan                   text NOT NULL DEFAULT 'monthly',
  status                 text NOT NULL DEFAULT 'active',
  created_at             timestamptz DEFAULT now()
);

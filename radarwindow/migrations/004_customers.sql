-- RadarWindow paying customers, written by the Stripe webhook.
-- Registration is gated to rows with status='active' (same pattern as CostWindow).

create table if not exists rw_customers (
    id                       uuid primary key default gen_random_uuid(),
    email                    text not null unique,
    plan                     text not null default 'radar',   -- 'radar' | 'radar_pro'
    status                   text not null default 'active',  -- 'active' | 'canceled' | 'past_due'
    stripe_customer_id       text,
    stripe_subscription_id   text,
    created_at               timestamptz not null default now(),
    updated_at               timestamptz not null default now()
);

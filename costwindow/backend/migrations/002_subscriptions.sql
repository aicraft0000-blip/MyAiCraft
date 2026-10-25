-- backend/migrations/002_subscriptions.sql
CREATE TABLE IF NOT EXISTS subscriptions (
    id          TEXT PRIMARY KEY DEFAULT gen_random_uuid()::text,
    user_id     UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    name        TEXT NOT NULL,
    cost_gbp    DECIMAL(10,2) NOT NULL,
    renewal_day INTEGER CHECK (renewal_day BETWEEN 1 AND 31),
    cancel_url  TEXT,
    is_active   BOOLEAN NOT NULL DEFAULT TRUE,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

ALTER TABLE subscriptions ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users manage own subscriptions"
ON subscriptions FOR ALL
USING (auth.uid() = user_id)
WITH CHECK (auth.uid() = user_id);

-- Add The Brief (UK Employment Law Specialist)
-- £29, Full + Compact editions, Stripe IDs from the owner 2026-05-17

INSERT OR IGNORE INTO products (id, type, name, slug, category, description, compatibility, price_pence, r2_key, r2_key_compact, stripe_price_id, stripe_product_id) VALUES (
  'agent_brief',
  'agent',
  'The Brief',
  'the-brief',
  'Legal',
  'Thinks like a litigator, not a helpline. Surfaces your Tribunal deadlines before anything else. Assesses your position honestly — the strengths, the weaknesses, what the other side will argue, and what to do next.',
  'Claude, ChatGPT, Gemini',
  2900,
  'agents/the-brief.md',
  'agents/the-brief-compact.md',
  'price_YOUR_PRICE_ID',
  'prod_YOUR_PRODUCT_ID'
);

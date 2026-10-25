-- Add The Accountant, The Scout, The Counsel, The Inspector
-- All £29, Full + Compact editions, Stripe IDs from the owner 2026-05-17

INSERT OR IGNORE INTO products (id, type, name, slug, category, description, compatibility, price_pence, r2_key, r2_key_compact, stripe_price_id, stripe_product_id) VALUES (
  'agent_accountant',
  'agent',
  'The Accountant',
  'the-accountant',
  'Finance',
  'Holds the full financial picture when you are too close to see it clearly. Triggers a Red Flag when a decision is driven by optimism rather than data. Tells you what your runway actually is.',
  'Claude, ChatGPT, Gemini',
  2900,
  'agents/the-accountant.md',
  'agents/the-accountant-compact.md',
  'price_YOUR_PRICE_ID',
  'prod_YOUR_PRODUCT_ID'
);

INSERT OR IGNORE INTO products (id, type, name, slug, category, description, compatibility, price_pence, r2_key, r2_key_compact, stripe_price_id, stripe_product_id) VALUES (
  'agent_scout',
  'agent',
  'The Scout',
  'the-scout',
  'Customer Intelligence',
  'Finds the real customer — not the one you want to exist. Operates on behaviour, not opinion. Tells you the truth about whether the market actually cares.',
  'Claude, ChatGPT, Gemini',
  2900,
  'agents/the-scout.md',
  'agents/the-scout-compact.md',
  'price_YOUR_PRICE_ID',
  'prod_YOUR_PRODUCT_ID'
);

INSERT OR IGNORE INTO products (id, type, name, slug, category, description, compatibility, price_pence, r2_key, r2_key_compact, stripe_price_id, stripe_product_id) VALUES (
  'agent_counsel',
  'agent',
  'The Counsel',
  'the-counsel',
  'Legal',
  'Makes sure you understand what you are agreeing to before you agree to it. Surfaces hidden obligations, attaches a risk register to every finding, tells you when you need a solicitor.',
  'Claude, ChatGPT, Gemini',
  2900,
  'agents/the-counsel.md',
  'agents/the-counsel-compact.md',
  'price_YOUR_PRICE_ID',
  'prod_YOUR_PRODUCT_ID'
);

INSERT OR IGNORE INTO products (id, type, name, slug, category, description, compatibility, price_pence, r2_key, r2_key_compact, stripe_price_id, stripe_product_id) VALUES (
  'agent_inspector',
  'agent',
  'The Inspector',
  'the-inspector',
  'Quality & Technical',
  'Finds what is broken before it matters. Delivers every finding as Observation, Evidence, Assessment, Recommendation — with named severity levels and a failure log that makes each review sharper than the last.',
  'Claude, ChatGPT, Gemini',
  2900,
  'agents/the-inspector.md',
  'agents/the-inspector-compact.md',
  'price_YOUR_PRICE_ID',
  'prod_YOUR_PRODUCT_ID'
);

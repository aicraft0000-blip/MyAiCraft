-- Add compact edition R2 key to products (nullable — only flagship agents have two editions)
ALTER TABLE products ADD COLUMN r2_key_compact TEXT;

-- Chief of Staff: compact edition
UPDATE products SET r2_key_compact = 'agents/chief-of-staff-compact.md' WHERE id = 'agent_chief_of_staff';

-- The Director: compact edition
UPDATE products SET r2_key_compact = 'agents/the-director-compact.md' WHERE id = 'agent_director';

-- Vigil: both editions
INSERT OR IGNORE INTO products (id, type, name, slug, category, description, compatibility, price_pence, r2_key, r2_key_compact) VALUES (
  'agent_vigil',
  'agent',
  'Vigil',
  'vigil',
  'Grief & Wellbeing',
  'A grief companion that reads what you need and becomes that — without platitudes, without flinching, without fixing. Holds the memory of who you have lost. Sits with the darkest thoughts without cementing them.',
  'Claude, ChatGPT, Gemini',
  1900,
  'agents/vigil.md',
  'agents/vigil-compact.md'
);

-- Marketplace: products, bundles, orders, library
-- Safe to apply to live DB: new tables only, no changes to existing tables.

CREATE TABLE IF NOT EXISTS products (
  id TEXT PRIMARY KEY,
  type TEXT NOT NULL CHECK(type IN ('skill', 'agent')),
  name TEXT NOT NULL,
  slug TEXT NOT NULL UNIQUE,
  category TEXT NOT NULL,
  description TEXT NOT NULL,
  compatibility TEXT NOT NULL,
  price_pence INTEGER NOT NULL CHECK(price_pence >= 0),
  r2_key TEXT NOT NULL,
  active INTEGER NOT NULL DEFAULT 1,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- idx_products_slug removed: UNIQUE on slug already creates an implicit index
CREATE INDEX IF NOT EXISTS idx_products_type ON products (type);
CREATE INDEX IF NOT EXISTS idx_products_active ON products (active);

CREATE TABLE IF NOT EXISTS bundles (
  id TEXT PRIMARY KEY,
  name TEXT NOT NULL,
  slug TEXT NOT NULL UNIQUE,
  description TEXT NOT NULL,
  price_pence INTEGER NOT NULL CHECK(price_pence >= 0),
  active INTEGER NOT NULL DEFAULT 1,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- idx_bundles_slug removed: UNIQUE on slug already creates an implicit index

CREATE TABLE IF NOT EXISTS bundle_items (
  bundle_id TEXT NOT NULL REFERENCES bundles(id),
  product_id TEXT NOT NULL REFERENCES products(id),
  PRIMARY KEY (bundle_id, product_id)
);

CREATE TABLE IF NOT EXISTS marketplace_orders (
  id TEXT PRIMARY KEY,
  account_id TEXT NOT NULL,
  stripe_session_id TEXT NOT NULL UNIQUE,
  stripe_customer_email TEXT,
  status TEXT NOT NULL DEFAULT 'pending' CHECK(status IN ('pending', 'completed')),
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_marketplace_orders_account ON marketplace_orders (account_id);
-- idx_marketplace_orders_session removed: UNIQUE on stripe_session_id already creates an implicit index

CREATE TABLE IF NOT EXISTS marketplace_order_items (
  id TEXT PRIMARY KEY,
  order_id TEXT NOT NULL REFERENCES marketplace_orders(id),
  product_id TEXT,
  bundle_id TEXT,
  CHECK((product_id IS NOT NULL) != (bundle_id IS NOT NULL))
);

CREATE INDEX IF NOT EXISTS idx_order_items_order ON marketplace_order_items (order_id);

CREATE TABLE IF NOT EXISTS marketplace_library (
  id TEXT PRIMARY KEY,
  account_id TEXT NOT NULL,
  product_id TEXT NOT NULL REFERENCES products(id),
  order_id TEXT NOT NULL REFERENCES marketplace_orders(id),
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  UNIQUE(account_id, product_id)
);

CREATE INDEX IF NOT EXISTS idx_library_account ON marketplace_library (account_id);

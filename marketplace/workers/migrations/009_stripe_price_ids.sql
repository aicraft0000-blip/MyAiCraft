-- Store Stripe price and product IDs against each product for reference
ALTER TABLE products ADD COLUMN stripe_price_id TEXT;
ALTER TABLE products ADD COLUMN stripe_product_id TEXT;

-- Vigil
UPDATE products SET
  stripe_price_id = 'price_YOUR_PRICE_ID',
  stripe_product_id = 'prod_YOUR_PRODUCT_ID'
WHERE id = 'agent_vigil';

-- Add is_free flag to products. Free products bypass checkout and download directly.
ALTER TABLE products ADD COLUMN is_free INTEGER NOT NULL DEFAULT 0;
UPDATE products SET is_free = 1 WHERE id IN ('skill_brand_brief', 'skill_excalidraw');

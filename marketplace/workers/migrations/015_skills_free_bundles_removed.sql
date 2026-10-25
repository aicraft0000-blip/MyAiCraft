-- 2026-06-17: All skills made free. Bundles category removed.

-- Set all skills to free (price £0, is_free flag)
UPDATE products
SET price_pence = 0, is_free = 1
WHERE type = 'skill';

-- Remove bundle items first (foreign key dependency)
DELETE FROM bundle_items;

-- Remove all bundles
DELETE FROM bundles;

-- Backfill category, region, value_chain_link from existing query_id (run after migration 008).
-- Idempotent: only fills where column is still NULL. One query_id per row so each row gets at most one of the three.

UPDATE candidate_articles
SET category = SUBSTRING(query_id FROM 5)
WHERE query_id IS NOT NULL AND query_id LIKE 'cat_%' AND (category IS NULL OR category = '');

UPDATE candidate_articles
SET region = REPLACE(SUBSTRING(query_id FROM 8), '_', ' ')
WHERE query_id IS NOT NULL AND query_id LIKE 'region_%' AND (region IS NULL OR region = '');

UPDATE candidate_articles
SET value_chain_link = REPLACE(SUBSTRING(query_id FROM 5), '_', ' ')
WHERE query_id IS NOT NULL AND query_id LIKE 'vcl_%' AND (value_chain_link IS NULL OR value_chain_link = '');

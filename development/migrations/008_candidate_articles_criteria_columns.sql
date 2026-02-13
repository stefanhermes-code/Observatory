-- Migration 008: Add category, region, value_chain_link to candidate_articles (per-candidate criteria for productivity)
-- Run in Supabase SQL Editor. Idempotent.
-- Each candidate can have one category, one region, and optionally one value_chain_link (from merged query_id attributions).

ALTER TABLE candidate_articles ADD COLUMN IF NOT EXISTS category TEXT;
ALTER TABLE candidate_articles ADD COLUMN IF NOT EXISTS region TEXT;
ALTER TABLE candidate_articles ADD COLUMN IF NOT EXISTS value_chain_link TEXT;

COMMENT ON COLUMN candidate_articles.category IS 'Category criterion this candidate is attributed to (from query_id cat_* or merged).';
COMMENT ON COLUMN candidate_articles.region IS 'Region criterion this candidate is attributed to (from query_id region_* or merged).';
COMMENT ON COLUMN candidate_articles.value_chain_link IS 'Value chain link criterion (from query_id vcl_* or merged). Optional.';

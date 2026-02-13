-- Migration 007: Add categories_count, regions_count, links_count to newsletter_runs (scope used in run)
-- Run in Supabase SQL Editor. Idempotent.

ALTER TABLE newsletter_runs ADD COLUMN IF NOT EXISTS categories_count SMALLINT;
ALTER TABLE newsletter_runs ADD COLUMN IF NOT EXISTS regions_count SMALLINT;
ALTER TABLE newsletter_runs ADD COLUMN IF NOT EXISTS links_count SMALLINT;

COMMENT ON COLUMN newsletter_runs.categories_count IS 'Number of categories from the spec used in this run.';
COMMENT ON COLUMN newsletter_runs.regions_count IS 'Number of regions from the spec used in this run.';
COMMENT ON COLUMN newsletter_runs.links_count IS 'Number of news items/links included in the generated report (from content_diagnostics.items_included).';

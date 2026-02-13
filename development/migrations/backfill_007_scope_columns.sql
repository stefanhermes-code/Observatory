-- Backfill categories_count, regions_count, links_count for existing newsletter_runs
-- Run in Supabase SQL Editor after migration 007. Idempotent (only fills where still NULL).

-- 1) categories_count and regions_count from the run's specification (current spec state)
-- Use jsonb_array_length only when the column is a jsonb array (safe for older DBs)
UPDATE newsletter_runs r
SET
  categories_count = (
    SELECT CASE WHEN jsonb_typeof(s.categories) = 'array' THEN jsonb_array_length(s.categories) ELSE NULL END
    FROM newsletter_specifications s WHERE s.id = r.specification_id
  ),
  regions_count = (
    SELECT CASE WHEN jsonb_typeof(s.regions) = 'array' THEN jsonb_array_length(s.regions) ELSE NULL END
    FROM newsletter_specifications s WHERE s.id = r.specification_id
  )
WHERE r.specification_id IS NOT NULL
  AND (r.categories_count IS NULL OR r.regions_count IS NULL);

-- 2) links_count from run metadata: content_diagnostics.items_included, else evidence_summary.inserted
UPDATE newsletter_runs r
SET links_count = COALESCE(
  (r.metadata->'content_diagnostics'->'items_included')::int,
  (r.metadata->'evidence_summary'->'inserted')::int
)
WHERE r.metadata IS NOT NULL
  AND r.links_count IS NULL
  AND (
    (r.metadata->'content_diagnostics'->'items_included') IS NOT NULL
    OR (r.metadata->'evidence_summary'->'inserted') IS NOT NULL
  );

-- 3) Verify: show counts of filled rows
SELECT
  COUNT(*) AS total_runs,
  COUNT(categories_count) AS with_categories_count,
  COUNT(regions_count) AS with_regions_count,
  COUNT(links_count) AS with_links_count
FROM newsletter_runs;

SELECT id, specification_id, created_at, categories_count, regions_count, links_count, status
FROM newsletter_runs
ORDER BY created_at DESC
LIMIT 15;

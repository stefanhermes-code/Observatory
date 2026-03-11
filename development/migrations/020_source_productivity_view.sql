-- Migration 020: Create DB-side aggregation view for Source Productivity.
-- Purpose: avoid Admin timeouts by aggregating candidate_articles per source in Postgres instead of in Python.
-- Apply in Supabase SQL Editor. Safe to re-run.

CREATE OR REPLACE VIEW public.source_productivity_vw AS
SELECT
  source_id,
  COALESCE(NULLIF(TRIM(source_name), ''), 'unknown') AS source_name,
  COUNT(*)::bigint AS count
FROM public.candidate_articles
GROUP BY source_id, COALESCE(NULLIF(TRIM(source_name), ''), 'unknown')
ORDER BY count DESC;

COMMENT ON VIEW public.source_productivity_vw IS
  'Admin reporting: candidate_articles count grouped by (source_id, source_name). Used by core.admin_db.get_source_productivity when available.';


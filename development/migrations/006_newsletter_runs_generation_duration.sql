-- Migration 006: Add generation_duration_seconds to newsletter_runs (time to generate, seconds)
-- Run in Supabase SQL Editor. Idempotent.

ALTER TABLE newsletter_runs
  ADD COLUMN IF NOT EXISTS generation_duration_seconds NUMERIC(10,1);

COMMENT ON COLUMN newsletter_runs.generation_duration_seconds IS 'Total generation time in seconds. Filled from evidence_summary.timing_seconds.total for new runs, or from (completed_at - created_at) when backfilled. NULL for failed or incomplete runs.';

-- Backfill existing rows: set duration from completed_at - created_at where still NULL
UPDATE newsletter_runs
SET generation_duration_seconds = ROUND(EXTRACT(EPOCH FROM (completed_at - created_at))::numeric, 1)
WHERE completed_at IS NOT NULL
  AND created_at IS NOT NULL
  AND generation_duration_seconds IS NULL;

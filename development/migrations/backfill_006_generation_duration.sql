-- Backfill generation_duration_seconds from created_at and completed_at
-- Run this in Supabase SQL Editor if the column is still empty after migration 006.
-- Then run the SELECT below to verify.

-- 1) Backfill: set duration = (completed_at - created_at) in seconds
UPDATE newsletter_runs
SET generation_duration_seconds = ROUND(
  EXTRACT(EPOCH FROM (
    (completed_at::timestamptz) - (created_at::timestamptz)
  ))::numeric,
  1
)
WHERE completed_at IS NOT NULL
  AND created_at IS NOT NULL;

-- 2) Verify: you should see non-null counts and a few sample rows
SELECT
  COUNT(*) AS total_rows,
  COUNT(created_at) AS with_created_at,
  COUNT(completed_at) AS with_completed_at,
  COUNT(generation_duration_seconds) AS with_duration
FROM newsletter_runs;

SELECT id, created_at, completed_at, generation_duration_seconds, status
FROM newsletter_runs
ORDER BY created_at DESC
LIMIT 10;

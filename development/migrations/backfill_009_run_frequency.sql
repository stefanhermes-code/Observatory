-- Backfill frequency for existing newsletter_runs from their specification
-- Run in Supabase SQL Editor after migration 009. Idempotent (only fills where still NULL).

UPDATE newsletter_runs r
SET frequency = s.frequency
FROM newsletter_specifications s
WHERE s.id = r.specification_id
  AND r.frequency IS NULL;

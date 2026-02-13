-- Migration 006: Add generation_duration_seconds to newsletter_runs (time to generate, seconds)
-- Run in Supabase SQL Editor. Idempotent.

ALTER TABLE newsletter_runs
  ADD COLUMN IF NOT EXISTS generation_duration_seconds NUMERIC(10,1);

COMMENT ON COLUMN newsletter_runs.generation_duration_seconds IS 'Total generation time in seconds (from evidence_summary.timing_seconds.total). NULL for failed or older runs.';

-- Migration 009: Add frequency (cadence) to newsletter_runs (cadence used for this run)
-- Run in Supabase SQL Editor. Idempotent.

ALTER TABLE newsletter_runs ADD COLUMN IF NOT EXISTS frequency TEXT;

COMMENT ON COLUMN newsletter_runs.frequency IS 'Cadence used for this run: daily, weekly, or monthly. Set at run creation from spec (or override).';

-- Migration 005: Index for get_recent_runs ORDER BY created_at DESC (avoids timeout)
-- Run in Supabase SQL Editor. Idempotent.

CREATE INDEX IF NOT EXISTS idx_newsletter_runs_created_at_desc
  ON newsletter_runs (created_at DESC);

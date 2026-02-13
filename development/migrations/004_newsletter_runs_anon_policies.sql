-- Migration 004: Allow anon to read/write newsletter_runs and read newsletter_specifications
-- Admin and Generator use the same anon key. Admin must SELECT runs (with spec name join); Generator must INSERT/UPDATE runs.
-- Run in Supabase SQL Editor. Idempotent.

-- newsletter_runs: anon can SELECT (Admin history), INSERT (Generator create run), UPDATE (Generator update status)
ALTER TABLE newsletter_runs ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "anon_select_newsletter_runs" ON newsletter_runs;
CREATE POLICY "anon_select_newsletter_runs"
  ON newsletter_runs FOR SELECT TO anon USING (true);

DROP POLICY IF EXISTS "anon_insert_newsletter_runs" ON newsletter_runs;
CREATE POLICY "anon_insert_newsletter_runs"
  ON newsletter_runs FOR INSERT TO anon WITH CHECK (true);

DROP POLICY IF EXISTS "anon_update_newsletter_runs" ON newsletter_runs;
CREATE POLICY "anon_update_newsletter_runs"
  ON newsletter_runs FOR UPDATE TO anon USING (true) WITH CHECK (true);

-- newsletter_specifications: anon must SELECT (for get_recent_runs join and Generator)
ALTER TABLE newsletter_specifications ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "anon_select_newsletter_specifications" ON newsletter_specifications;
CREATE POLICY "anon_select_newsletter_specifications"
  ON newsletter_specifications FOR SELECT TO anon USING (true);

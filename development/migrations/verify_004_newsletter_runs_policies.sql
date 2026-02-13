-- Verify migration 004 (newsletter_runs / newsletter_specifications RLS policies) has been applied.
-- Run in Supabase SQL Editor after running 004_newsletter_runs_anon_policies.sql.
--
-- Expected: All rows show status 'OK'. Then open Admin app → Generation History; runs should appear.

SELECT 'RLS on newsletter_runs' AS check_name,
  CASE WHEN EXISTS (
    SELECT 1 FROM pg_class c
    JOIN pg_namespace n ON c.relnamespace = n.oid
    WHERE n.nspname = 'public' AND c.relname = 'newsletter_runs' AND c.relrowsecurity = true
  ) THEN 'OK' ELSE 'MISSING' END AS status
UNION ALL
SELECT 'RLS on newsletter_specifications',
  CASE WHEN EXISTS (
    SELECT 1 FROM pg_class c
    JOIN pg_namespace n ON c.relnamespace = n.oid
    WHERE n.nspname = 'public' AND c.relname = 'newsletter_specifications' AND c.relrowsecurity = true
  ) THEN 'OK' ELSE 'MISSING' END
UNION ALL
SELECT 'Policy: anon_select_newsletter_runs',
  CASE WHEN EXISTS (SELECT 1 FROM pg_policies WHERE schemaname = 'public' AND tablename = 'newsletter_runs' AND policyname = 'anon_select_newsletter_runs') THEN 'OK' ELSE 'MISSING' END
UNION ALL
SELECT 'Policy: anon_insert_newsletter_runs',
  CASE WHEN EXISTS (SELECT 1 FROM pg_policies WHERE schemaname = 'public' AND tablename = 'newsletter_runs' AND policyname = 'anon_insert_newsletter_runs') THEN 'OK' ELSE 'MISSING' END
UNION ALL
SELECT 'Policy: anon_update_newsletter_runs',
  CASE WHEN EXISTS (SELECT 1 FROM pg_policies WHERE schemaname = 'public' AND tablename = 'newsletter_runs' AND policyname = 'anon_update_newsletter_runs') THEN 'OK' ELSE 'MISSING' END
UNION ALL
SELECT 'Policy: anon_select_newsletter_specifications',
  CASE WHEN EXISTS (SELECT 1 FROM pg_policies WHERE schemaname = 'public' AND tablename = 'newsletter_specifications' AND policyname = 'anon_select_newsletter_specifications') THEN 'OK' ELSE 'MISSING' END
ORDER BY check_name;

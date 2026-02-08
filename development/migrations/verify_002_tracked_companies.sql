-- Verify migration 002 (tracked_companies) has been fully applied.
-- Run in Supabase SQL Editor. All rows should show status 'OK'.

SELECT 'Table: tracked_companies' AS check_name,
  CASE WHEN EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema = 'public' AND table_name = 'tracked_companies') THEN 'OK' ELSE 'MISSING' END AS status
UNION ALL
SELECT 'Unique on name',
  CASE WHEN EXISTS (SELECT 1 FROM pg_constraint c JOIN pg_class t ON c.conrelid = t.oid WHERE t.relname = 'tracked_companies' AND c.contype = 'u')
    OR EXISTS (SELECT 1 FROM pg_indexes WHERE schemaname = 'public' AND tablename = 'tracked_companies' AND indexdef LIKE '%UNIQUE%')
  THEN 'OK' ELSE 'MISSING' END
UNION ALL
SELECT 'Index: ix_tracked_companies_status',
  CASE WHEN EXISTS (SELECT 1 FROM pg_indexes WHERE schemaname = 'public' AND indexname = 'ix_tracked_companies_status') THEN 'OK' ELSE 'MISSING' END
UNION ALL
SELECT 'Index: ix_tracked_companies_name',
  CASE WHEN EXISTS (SELECT 1 FROM pg_indexes WHERE schemaname = 'public' AND indexname = 'ix_tracked_companies_name') THEN 'OK' ELSE 'MISSING' END
ORDER BY check_name;

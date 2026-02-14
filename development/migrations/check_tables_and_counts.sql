-- Run in Supabase SQL Editor: list all public tables and row counts.
-- Use this to see which tables exist, which have data, and compare with the app's expected tables.

SELECT
  schemaname AS schema_name,
  relname AS table_name,
  n_live_tup AS row_count
FROM pg_stat_user_tables
WHERE schemaname = 'public'
ORDER BY relname;

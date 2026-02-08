-- Verify V2 migration (001_v2_sources_and_evidence.sql) has been fully applied.
-- Run in Supabase SQL Editor. All rows should show status 'OK'.

-- Report: one row per check. Any 'MISSING' means re-run the migration.
SELECT 'Enum: source_type' AS check_name,
  CASE WHEN EXISTS (SELECT 1 FROM pg_type WHERE typname = 'source_type') THEN 'OK' ELSE 'MISSING' END AS status
UNION ALL
SELECT 'Enum: url_validation_status',
  CASE WHEN EXISTS (SELECT 1 FROM pg_type WHERE typname = 'url_validation_status') THEN 'OK' ELSE 'MISSING' END
UNION ALL
SELECT 'Enum: signal_type',
  CASE WHEN EXISTS (SELECT 1 FROM pg_type WHERE typname = 'signal_type') THEN 'OK' ELSE 'MISSING' END
UNION ALL
SELECT 'Table: sources',
  CASE WHEN EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema = 'public' AND table_name = 'sources') THEN 'OK' ELSE 'MISSING' END
UNION ALL
SELECT 'Table: candidate_articles',
  CASE WHEN EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema = 'public' AND table_name = 'candidate_articles') THEN 'OK' ELSE 'MISSING' END
UNION ALL
SELECT 'Table: signals',
  CASE WHEN EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema = 'public' AND table_name = 'signals') THEN 'OK' ELSE 'MISSING' END
UNION ALL
SELECT 'Table: signal_occurrences',
  CASE WHEN EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema = 'public' AND table_name = 'signal_occurrences') THEN 'OK' ELSE 'MISSING' END
UNION ALL
SELECT 'Table: run_feedback',
  CASE WHEN EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema = 'public' AND table_name = 'run_feedback') THEN 'OK' ELSE 'MISSING' END
UNION ALL
SELECT 'Constraint: sources_workspace_id_null',
  CASE WHEN EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'sources_workspace_id_null') THEN 'OK' ELSE 'MISSING' END
UNION ALL
SELECT 'Index: ux_candidate_articles_run_canonical',
  CASE WHEN EXISTS (SELECT 1 FROM pg_indexes WHERE schemaname = 'public' AND indexname = 'ux_candidate_articles_run_canonical') THEN 'OK' ELSE 'MISSING' END
UNION ALL
SELECT 'Index: ix_candidate_articles_workspace_spec',
  CASE WHEN EXISTS (SELECT 1 FROM pg_indexes WHERE schemaname = 'public' AND indexname = 'ix_candidate_articles_workspace_spec') THEN 'OK' ELSE 'MISSING' END
UNION ALL
SELECT 'Index: ix_candidate_articles_published_at',
  CASE WHEN EXISTS (SELECT 1 FROM pg_indexes WHERE schemaname = 'public' AND indexname = 'ix_candidate_articles_published_at') THEN 'OK' ELSE 'MISSING' END
UNION ALL
SELECT 'Index: ix_signal_occurrences_ws_spec',
  CASE WHEN EXISTS (SELECT 1 FROM pg_indexes WHERE schemaname = 'public' AND indexname = 'ix_signal_occurrences_ws_spec') THEN 'OK' ELSE 'MISSING' END
UNION ALL
SELECT 'Index: ix_signal_occurrences_run',
  CASE WHEN EXISTS (SELECT 1 FROM pg_indexes WHERE schemaname = 'public' AND indexname = 'ix_signal_occurrences_run') THEN 'OK' ELSE 'MISSING' END
ORDER BY check_name;

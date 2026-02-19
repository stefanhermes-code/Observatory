-- Verification for migration 011 (signal_clusters). Run AFTER 011_signal_clusters.sql.
-- One statement; expected: 4 rows, all passed = true.

SELECT * FROM (
  SELECT 1 AS step, 'Enum cluster_classification exists' AS check_name,
         1 AS expected,
         (SELECT count(*) FROM pg_type WHERE typname = 'cluster_classification') AS actual,
         (SELECT count(*) FROM pg_type WHERE typname = 'cluster_classification') = 1 AS passed
  UNION ALL
  SELECT 2, 'Table signal_clusters exists',
         1,
         (SELECT count(*) FROM information_schema.tables WHERE table_schema = 'public' AND table_name = 'signal_clusters'),
         (SELECT count(*) FROM information_schema.tables WHERE table_schema = 'public' AND table_name = 'signal_clusters') = 1
  UNION ALL
  SELECT 3, 'signal_clusters has 12 columns',
         12,
         (SELECT count(*) FROM information_schema.columns WHERE table_schema = 'public' AND table_name = 'signal_clusters'),
         (SELECT count(*) FROM information_schema.columns WHERE table_schema = 'public' AND table_name = 'signal_clusters') = 12
  UNION ALL
  SELECT 4, 'signal_clusters has at least 4 indexes',
         4,
         (SELECT count(*) FROM pg_indexes WHERE schemaname = 'public' AND tablename = 'signal_clusters'),
         (SELECT count(*) FROM pg_indexes WHERE schemaname = 'public' AND tablename = 'signal_clusters') >= 4
) AS checks
ORDER BY step;

-- Verify Phase 4 doctrine columns on signal_clusters (run after 012 in Supabase SQL Editor).
-- Single SELECT: all checks must return true.
SELECT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'signal_clusters' AND column_name = 'final_classification') AS has_final_classification
UNION ALL
SELECT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'signal_clusters' AND column_name = 'override_source')
UNION ALL
SELECT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'signal_clusters' AND column_name = 'materiality_flag')
UNION ALL
SELECT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'signal_clusters' AND column_name = 'override_reason')
UNION ALL
SELECT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'signal_clusters' AND column_name = 'trend_multi_year');

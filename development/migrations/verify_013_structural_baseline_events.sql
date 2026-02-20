-- Verify Phase 5A structural_baseline_events table (run after 013 in Supabase SQL Editor).
-- All checks should return true.
SELECT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema = 'public' AND table_name = 'structural_baseline_events') AS table_exists
UNION ALL
SELECT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'structural_baseline_events' AND column_name = 'event_date')
UNION ALL
SELECT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'structural_baseline_events' AND column_name = 'year')
UNION ALL
SELECT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'structural_baseline_events' AND column_name = 'signal_type');

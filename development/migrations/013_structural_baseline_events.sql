-- Migration 013: Phase 5A – structural_baseline_events (curated 2020–2024 seed)
-- Apply in Supabase SQL Editor. Idempotent.
-- Separate from weekly observatory runs; used for Phase 5B annual baseline.

CREATE TABLE IF NOT EXISTS structural_baseline_events (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  event_date DATE NOT NULL,
  year INT NOT NULL,
  company_name TEXT NOT NULL,
  region_macro TEXT NOT NULL CHECK (region_macro IN ('EMEA', 'APAC', 'Americas')),
  country TEXT NULL,
  segment TEXT NOT NULL CHECK (segment IN ('raw_materials', 'flexible_foam', 'rigid_foam', 'tpu', 'case')),
  signal_type TEXT NOT NULL CHECK (signal_type IN ('capacity', 'mna', 'regulation', 'technology', 'investment', 'demand')),
  numeric_value DOUBLE PRECISION NULL,
  numeric_unit TEXT NULL CHECK (numeric_unit IS NULL OR numeric_unit IN ('TPA', 'percent', 'USD', 'EUR')),
  direction TEXT NULL CHECK (direction IS NULL OR direction IN ('increase', 'decrease', 'neutral')),
  description TEXT NOT NULL,
  source_name TEXT NOT NULL,
  source_url TEXT NULL,
  notes TEXT NULL,
  final_classification TEXT NOT NULL DEFAULT 'structural',
  materiality_flag BOOLEAN NOT NULL DEFAULT true,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS ix_structural_baseline_events_year ON structural_baseline_events(year);
CREATE INDEX IF NOT EXISTS ix_structural_baseline_events_region_macro ON structural_baseline_events(region_macro);
CREATE INDEX IF NOT EXISTS ix_structural_baseline_events_segment ON structural_baseline_events(segment);
CREATE INDEX IF NOT EXISTS ix_structural_baseline_events_signal_type ON structural_baseline_events(signal_type);
CREATE INDEX IF NOT EXISTS ix_structural_baseline_events_event_date ON structural_baseline_events(event_date);

COMMENT ON TABLE structural_baseline_events IS 'Phase 5A: Curated structural events 2020–2024 for baseline. Not overwritten by weekly runs.';

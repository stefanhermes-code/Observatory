-- Migration 011: V2 Build Spec Phase 2 – signal_clusters table
-- Apply in Supabase SQL Editor. Idempotent.
-- Run after 010. Clustering groups extracted_signals by (company_name, signal_type, region, segment) per run.

DO $$ BEGIN
  CREATE TYPE cluster_classification AS ENUM (
    'noise',
    'tactical',
    'cyclical',
    'structural',
    'transformational'
  );
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

CREATE TABLE IF NOT EXISTS signal_clusters (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  run_id UUID NOT NULL REFERENCES newsletter_runs(id) ON DELETE CASCADE,
  cluster_key TEXT NOT NULL,
  signal_type extracted_signal_type NOT NULL DEFAULT 'other',
  region TEXT NULL,
  segment extracted_segment NOT NULL DEFAULT 'unknown',
  aggregated_numeric_value DOUBLE PRECISION NULL,
  aggregated_numeric_unit TEXT NULL,
  cluster_size INT NOT NULL DEFAULT 0,
  structural_weight DOUBLE PRECISION NOT NULL DEFAULT 0,
  classification cluster_classification NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS ix_signal_clusters_run_id ON signal_clusters(run_id);
CREATE INDEX IF NOT EXISTS ix_signal_clusters_cluster_key ON signal_clusters(cluster_key);
CREATE INDEX IF NOT EXISTS ix_signal_clusters_signal_type ON signal_clusters(signal_type);
CREATE INDEX IF NOT EXISTS ix_signal_clusters_classification ON signal_clusters(classification);

COMMENT ON TABLE signal_clusters IS 'V2 Build Spec Phase 2: clusters of extracted_signals by company_name+signal_type+region+segment per run. Classification filled in Phase 3.';

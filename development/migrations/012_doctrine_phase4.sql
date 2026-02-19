-- Migration 012: V2 Build Spec Phase 4 – Doctrine Resolver output fields
-- Apply in Supabase SQL Editor. Idempotent. Run after 011.
-- Stores final_classification, override_source, materiality_flag, override_reason, trend_multi_year.
-- classification column = llm_classification (set by Phase 3); do not overwrite when applying doctrine.

DO $$ BEGIN
  CREATE TYPE override_source_type AS ENUM ('llm', 'doctrine');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

ALTER TABLE signal_clusters ADD COLUMN IF NOT EXISTS final_classification cluster_classification NULL;
ALTER TABLE signal_clusters ADD COLUMN IF NOT EXISTS override_source override_source_type NULL;
ALTER TABLE signal_clusters ADD COLUMN IF NOT EXISTS materiality_flag BOOLEAN NOT NULL DEFAULT false;
ALTER TABLE signal_clusters ADD COLUMN IF NOT EXISTS override_reason TEXT NULL;
ALTER TABLE signal_clusters ADD COLUMN IF NOT EXISTS trend_multi_year BOOLEAN NULL;

CREATE INDEX IF NOT EXISTS ix_signal_clusters_final_classification ON signal_clusters(final_classification);

COMMENT ON COLUMN signal_clusters.classification IS 'Phase 3: LLM classification (llm_classification). Do not overwrite after doctrine.';
COMMENT ON COLUMN signal_clusters.final_classification IS 'Phase 4: Doctrine Resolver output.';
COMMENT ON COLUMN signal_clusters.override_source IS 'Phase 4: llm or doctrine.';
COMMENT ON COLUMN signal_clusters.materiality_flag IS 'Phase 4: true when doctrine marks cluster as material.';
COMMENT ON COLUMN signal_clusters.trend_multi_year IS 'Phase 4: demand only; true if multi-year trend (else default cyclical).';

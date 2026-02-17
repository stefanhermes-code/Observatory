-- Migration 010: V2 Build Spec Phase 1 – extracted_signals table
-- Apply in Supabase SQL Editor. Idempotent.
-- Used by signal extraction layer: one row per extracted signal per article.

-- Enums for extracted_signals (spec: segment, signal_type, time_horizon)
DO $$ BEGIN
  CREATE TYPE extracted_segment AS ENUM (
    'flexible_foam',
    'rigid_foam',
    'tpu',
    'case',
    'elastomers',
    'raw_materials',
    'mixed',
    'unknown'
  );
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
  CREATE TYPE extracted_signal_type AS ENUM (
    'capacity',
    'investment',
    'mna',
    'regulation',
    'feedstock',
    'demand',
    'sustainability',
    'price',
    'operational',
    'other'
  );
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
  CREATE TYPE time_horizon_type AS ENUM (
    'short_term',
    'cyclical',
    'structural',
    'unknown'
  );
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

-- Table: extracted_signals (one row per signal extracted from one article)
CREATE TABLE IF NOT EXISTS extracted_signals (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  run_id UUID NOT NULL REFERENCES newsletter_runs(id) ON DELETE CASCADE,
  article_id UUID NOT NULL REFERENCES candidate_articles(id) ON DELETE CASCADE,

  company_name TEXT NULL,
  segment extracted_segment NOT NULL DEFAULT 'unknown',
  region TEXT NULL,
  signal_type extracted_signal_type NOT NULL DEFAULT 'other',

  numeric_value DOUBLE PRECISION NULL,
  numeric_unit TEXT NULL,
  currency TEXT NULL,

  time_horizon time_horizon_type NOT NULL DEFAULT 'unknown',
  confidence_score DOUBLE PRECISION NOT NULL DEFAULT 0,
  CONSTRAINT extracted_signals_confidence_range CHECK (confidence_score >= 0 AND confidence_score <= 1),

  raw_json JSONB NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS ix_extracted_signals_run_id ON extracted_signals(run_id);
CREATE INDEX IF NOT EXISTS ix_extracted_signals_article_id ON extracted_signals(article_id);
CREATE INDEX IF NOT EXISTS ix_extracted_signals_signal_type ON extracted_signals(signal_type);
CREATE INDEX IF NOT EXISTS ix_extracted_signals_region ON extracted_signals(region);

COMMENT ON TABLE extracted_signals IS 'V2 Build Spec Phase 1: structured signals extracted from candidate_articles via LLM.';

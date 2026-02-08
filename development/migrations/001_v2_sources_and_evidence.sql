-- Migration 001: V2 sources and evidence tables
-- Apply in Supabase SQL Editor. Idempotent (safe to run once).

-- 1) Enums
DO $$ BEGIN
  CREATE TYPE source_type AS ENUM ('rss','sitemap','html_list','search');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
  CREATE TYPE url_validation_status AS ENUM ('valid_2xx','valid_3xx','restricted_403','error_other','not_checked');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
  CREATE TYPE signal_type AS ENUM (
    'capacity_assets',
    'regulation_standards',
    'mna_partnerships',
    'pricing_feedstocks',
    'demand_enduse',
    'technology_recycling',
    'competitive_actions',
    'safety_incidents',
    'other'
  );
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

-- 2) Sources (global admin registry)
CREATE TABLE IF NOT EXISTS sources (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  workspace_id UUID NULL,
  source_name TEXT NOT NULL,
  source_type source_type NOT NULL,
  base_url TEXT NOT NULL,
  rss_url TEXT NULL,
  sitemap_url TEXT NULL,
  list_url TEXT NULL,
  selectors JSONB NULL,
  trust_tier INT NOT NULL DEFAULT 2,
  enabled BOOLEAN NOT NULL DEFAULT TRUE,
  notes TEXT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

DO $$ BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'sources_workspace_id_null') THEN
    ALTER TABLE sources ADD CONSTRAINT sources_workspace_id_null CHECK (workspace_id IS NULL);
  END IF;
END $$;

-- 3) Candidate articles (evidence set per run)
CREATE TABLE IF NOT EXISTS candidate_articles (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  workspace_id UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
  specification_id UUID NOT NULL REFERENCES newsletter_specifications(id) ON DELETE CASCADE,
  run_id UUID NOT NULL REFERENCES newsletter_runs(id) ON DELETE CASCADE,

  source_id UUID NULL REFERENCES sources(id) ON DELETE SET NULL,
  source_name TEXT NOT NULL,

  query_id TEXT NULL,
  query_text TEXT NULL,

  url TEXT NOT NULL,
  canonical_url TEXT NOT NULL,
  title TEXT NULL,
  snippet TEXT NULL,
  published_at DATE NULL,

  validation_status url_validation_status NOT NULL DEFAULT 'not_checked',
  http_status INT NULL,

  retrieved_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE UNIQUE INDEX IF NOT EXISTS ux_candidate_articles_run_canonical
  ON candidate_articles(run_id, canonical_url);

CREATE INDEX IF NOT EXISTS ix_candidate_articles_workspace_spec
  ON candidate_articles(workspace_id, specification_id);

CREATE INDEX IF NOT EXISTS ix_candidate_articles_published_at
  ON candidate_articles(published_at);

-- 4) Signals
CREATE TABLE IF NOT EXISTS signals (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  canonical_url TEXT NULL,
  title TEXT NOT NULL,
  summary TEXT NOT NULL,

  signal_type signal_type NOT NULL DEFAULT 'other',
  companies JSONB NULL,
  regions JSONB NULL,
  value_chain_links JSONB NULL,

  confidence INT NOT NULL DEFAULT 3,

  first_seen_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  last_seen_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- 5) Signal occurrences
CREATE TABLE IF NOT EXISTS signal_occurrences (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  signal_id UUID NOT NULL REFERENCES signals(id) ON DELETE CASCADE,
  workspace_id UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
  specification_id UUID NOT NULL REFERENCES newsletter_specifications(id) ON DELETE CASCADE,
  run_id UUID NOT NULL REFERENCES newsletter_runs(id) ON DELETE CASCADE,
  candidate_article_id UUID NULL REFERENCES candidate_articles(id) ON DELETE SET NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS ix_signal_occurrences_ws_spec
  ON signal_occurrences(workspace_id, specification_id);

CREATE INDEX IF NOT EXISTS ix_signal_occurrences_run
  ON signal_occurrences(run_id);

-- 6) Run feedback (optional)
CREATE TABLE IF NOT EXISTS run_feedback (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  workspace_id UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
  specification_id UUID NOT NULL REFERENCES newsletter_specifications(id) ON DELETE CASCADE,
  run_id UUID NOT NULL REFERENCES newsletter_runs(id) ON DELETE CASCADE,
  user_email TEXT NOT NULL,
  usefulness INT NULL,
  accuracy INT NULL,
  timeliness INT NULL,
  notes TEXT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- DATA_MODEL_V2.sql
-- V2 additions: sources (global), candidate_articles, signals, signal_occurrences
-- Metadata-only storage.

-- 1) Enums (optional; can also be TEXT with check constraints)
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
  workspace_id UUID NULL, -- MUST stay NULL (global-only)
  source_name TEXT NOT NULL,
  source_type source_type NOT NULL,
  base_url TEXT NOT NULL,
  rss_url TEXT NULL,
  sitemap_url TEXT NULL,
  list_url TEXT NULL,
  selectors JSONB NULL,
  trust_tier INT NOT NULL DEFAULT 2, -- 1..4
  enabled BOOLEAN NOT NULL DEFAULT TRUE,
  notes TEXT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Enforce global-only:
ALTER TABLE sources
  ADD CONSTRAINT sources_workspace_id_null CHECK (workspace_id IS NULL);

-- 3) Candidate articles (evidence set per run)
CREATE TABLE IF NOT EXISTS candidate_articles (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  workspace_id UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
  specification_id UUID NOT NULL REFERENCES newsletter_specifications(id) ON DELETE CASCADE,
  run_id UUID NOT NULL REFERENCES newsletter_runs(id) ON DELETE CASCADE,

  source_id UUID NULL REFERENCES sources(id) ON DELETE SET NULL,
  source_name TEXT NOT NULL,

  query_id TEXT NULL,            -- for search results
  query_text TEXT NULL,          -- stored for transparency/debug

  url TEXT NOT NULL,
  canonical_url TEXT NOT NULL,
  title TEXT NULL,
  snippet TEXT NULL,
  published_at DATE NULL,

  validation_status url_validation_status NOT NULL DEFAULT 'not_checked',
  http_status INT NULL,

  retrieved_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Unique per run to prevent duplicates:
CREATE UNIQUE INDEX IF NOT EXISTS ux_candidate_articles_run_canonical
ON candidate_articles(run_id, canonical_url);

CREATE INDEX IF NOT EXISTS ix_candidate_articles_workspace_spec
ON candidate_articles(workspace_id, specification_id);

CREATE INDEX IF NOT EXISTS ix_candidate_articles_published_at
ON candidate_articles(published_at);

-- 4) Signals (normalized “events”)
CREATE TABLE IF NOT EXISTS signals (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  canonical_url TEXT NULL, -- optional stable key; can also be a hash of title+date+entity
  title TEXT NOT NULL,
  summary TEXT NOT NULL,

  signal_type signal_type NOT NULL DEFAULT 'other',
  companies JSONB NULL,          -- array of company names/ids (metadata-level)
  regions JSONB NULL,            -- array
  value_chain_links JSONB NULL,  -- array

  confidence INT NOT NULL DEFAULT 3, -- 1..5

  first_seen_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  last_seen_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- 5) Signal occurrences (ties signals to runs/specs/workspaces)
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

-- Optional: feedback (can be phase 2+)
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

-- Migration 002: Tracked companies (PU industry companies for query planning / evidence).
-- Global table; seed from development/company_list.json.

CREATE TABLE IF NOT EXISTS tracked_companies (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name TEXT NOT NULL,
  aliases JSONB NOT NULL DEFAULT '[]',
  value_chain_position JSONB NOT NULL DEFAULT '[]',
  regions JSONB NOT NULL DEFAULT '[]',
  status TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'inactive')),
  notes TEXT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE(name)
);

CREATE INDEX IF NOT EXISTS ix_tracked_companies_status ON tracked_companies(status);
CREATE INDEX IF NOT EXISTS ix_tracked_companies_name ON tracked_companies(name);

COMMENT ON TABLE tracked_companies IS 'PU industry companies to track for evidence/search; seeded from company_list.json';

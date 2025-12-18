-- PU Observatory Platform - Supabase Database Schema
-- Run this in Supabase SQL Editor

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ============================================
-- 1. SPECIFICATION REQUESTS (Configurator)
-- ============================================
CREATE TABLE specification_requests (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    newsletter_name VARCHAR(255) NOT NULL,
    industry_code VARCHAR(50) NOT NULL DEFAULT 'PU',
    categories JSONB NOT NULL, -- Array of category IDs
    regions JSONB NOT NULL, -- Array of region names
    frequency VARCHAR(20) NOT NULL CHECK (frequency IN ('daily', 'weekly', 'monthly')),
    company_name VARCHAR(255) NOT NULL,
    contact_email VARCHAR(255) NOT NULL,
    first_name VARCHAR(255),
    last_name VARCHAR(255),
    street VARCHAR(255),
    house_number VARCHAR(50),
    city VARCHAR(255),
    zip_code VARCHAR(50),
    country VARCHAR(255),
    vat_number VARCHAR(100),
    submission_timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    status VARCHAR(50) NOT NULL DEFAULT 'pending_review' CHECK (status IN ('pending_review', 'approved', 'rejected', 'on_hold')),
    admin_notes TEXT,
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_spec_requests_status ON specification_requests(status);
CREATE INDEX idx_spec_requests_submission ON specification_requests(submission_timestamp DESC);

-- ============================================
-- 2. WORKSPACES
-- ============================================
CREATE TABLE workspaces (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL,
    company_name VARCHAR(255) NOT NULL,
    contact_email VARCHAR(255) NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_workspaces_company ON workspaces(company_name);

-- ============================================
-- 3. WORKSPACE MEMBERS
-- ============================================
CREATE TABLE workspace_members (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    workspace_id UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    user_email VARCHAR(255) NOT NULL,
    role VARCHAR(50) NOT NULL DEFAULT 'member' CHECK (role IN ('owner', 'manager', 'member')),
    added_at TIMESTAMPTZ DEFAULT NOW(),
    added_by VARCHAR(255),
    UNIQUE(workspace_id, user_email)
);

CREATE INDEX idx_workspace_members_email ON workspace_members(user_email);
CREATE INDEX idx_workspace_members_workspace ON workspace_members(workspace_id);

-- ============================================
-- 4. SPECIFICATIONS (Active Newsletter Specs)
-- Note: Code uses "newsletter_specifications" table name
-- ============================================
CREATE TABLE newsletter_specifications (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    workspace_id UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    newsletter_name VARCHAR(255) NOT NULL,
    industry_code VARCHAR(50) NOT NULL DEFAULT 'PU',
    categories JSONB NOT NULL, -- Array of category IDs
    regions JSONB NOT NULL, -- Array of region names
    frequency VARCHAR(20) NOT NULL CHECK (frequency IN ('daily', 'weekly', 'monthly')),
    status VARCHAR(50) NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'paused', 'cancelled')),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    activated_at TIMESTAMPTZ,
    paused_at TIMESTAMPTZ,
    created_by VARCHAR(255),
    notes TEXT
);

CREATE INDEX idx_specifications_workspace ON newsletter_specifications(workspace_id);
CREATE INDEX idx_specifications_status ON newsletter_specifications(status);

-- ============================================
-- 5. NEWSLETTER RUNS (Generation History)
-- ============================================
CREATE TABLE newsletter_runs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    specification_id UUID NOT NULL REFERENCES newsletter_specifications(id) ON DELETE CASCADE,
    workspace_id UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    user_email VARCHAR(255) NOT NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'running' CHECK (status IN ('running', 'success', 'failed')),
    artifact_path VARCHAR(500), -- Path in Supabase Storage
    cadence_period_key VARCHAR(50), -- e.g., "2025-01-15" for daily, "2025-W03" for weekly, "2025-01" for monthly
    error_message TEXT,
    metadata JSONB, -- Store model, tokens, etc.
    created_at TIMESTAMPTZ DEFAULT NOW(),
    completed_at TIMESTAMPTZ
);

CREATE INDEX idx_runs_specification ON newsletter_runs(specification_id);
CREATE INDEX idx_runs_workspace ON newsletter_runs(workspace_id);
CREATE INDEX idx_runs_status ON newsletter_runs(status);
CREATE INDEX idx_runs_cadence ON newsletter_runs(specification_id, cadence_period_key);

-- ============================================
-- 6. AUDIT LOGS (Admin Actions)
-- Note: Code uses "audit_log" table name
-- ============================================
CREATE TABLE audit_log (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    action_type VARCHAR(100) NOT NULL, -- e.g., 'spec_approved', 'workspace_created', 'frequency_override'
    actor_email VARCHAR(255) NOT NULL,
    target_type VARCHAR(100), -- e.g., 'specification', 'workspace', 'run'
    target_id UUID,
    details JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_audit_log_actor ON audit_log(actor_email);
CREATE INDEX idx_audit_log_type ON audit_log(action_type);
CREATE INDEX idx_audit_log_created ON audit_log(created_at DESC);

-- ============================================
-- 7. OPTIONAL: CATEGORIES (Override taxonomy.py)
-- ============================================
CREATE TABLE categories (
    id VARCHAR(50) PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    display_order INTEGER,
    active BOOLEAN DEFAULT TRUE
);

-- ============================================
-- 8. OPTIONAL: REGIONS (Override taxonomy.py)
-- ============================================
CREATE TABLE regions (
    id VARCHAR(50) PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    display_order INTEGER,
    active BOOLEAN DEFAULT TRUE
);

-- ============================================
-- FUNCTIONS & TRIGGERS
-- ============================================

-- Auto-update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_workspaces_updated_at BEFORE UPDATE ON workspaces
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_specification_requests_updated_at BEFORE UPDATE ON specification_requests
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- ============================================
-- COMMENTS
-- ============================================
COMMENT ON TABLE specification_requests IS 'Public submissions from Configurator app';
COMMENT ON TABLE workspaces IS 'Workspace/company entities';
COMMENT ON TABLE workspace_members IS 'User-workspace relationships';
COMMENT ON TABLE newsletter_specifications IS 'Active newsletter specifications';
COMMENT ON TABLE newsletter_runs IS 'Newsletter generation history';
COMMENT ON TABLE audit_log IS 'Admin action audit trail';


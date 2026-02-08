-- Migration 003: Add categories to tracked_companies (match spec taxonomy).
ALTER TABLE tracked_companies ADD COLUMN IF NOT EXISTS categories JSONB NOT NULL DEFAULT '[]';

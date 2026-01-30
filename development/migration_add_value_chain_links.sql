-- Migration: Add value_chain_links column to specification tables
-- This allows storing which specific value chain links are selected for a specification
-- Run this migration in your Supabase SQL editor

-- Add value_chain_links column to specification_requests table
ALTER TABLE specification_requests 
ADD COLUMN IF NOT EXISTS value_chain_links JSONB DEFAULT '[]'::jsonb;

-- Add value_chain_links column to newsletter_specifications table
ALTER TABLE newsletter_specifications 
ADD COLUMN IF NOT EXISTS value_chain_links JSONB DEFAULT '[]'::jsonb;

-- Add comment to document the column
COMMENT ON COLUMN specification_requests.value_chain_links IS 'Array of value chain link IDs (e.g., ["raw_materials", "system_houses"]) selected for this specification';
COMMENT ON COLUMN newsletter_specifications.value_chain_links IS 'Array of value chain link IDs (e.g., ["raw_materials", "system_houses"]) selected for this specification';

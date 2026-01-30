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

-- ============================================
-- VERIFICATION QUERIES (Run these to check if migration worked)
-- ============================================

-- Check if value_chain_links column exists in newsletter_specifications table
SELECT 
    column_name, 
    data_type, 
    column_default
FROM information_schema.columns 
WHERE table_name = 'newsletter_specifications' 
  AND column_name = 'value_chain_links';

-- Check if value_chain_links column exists in specification_requests table
SELECT 
    column_name, 
    data_type, 
    column_default
FROM information_schema.columns 
WHERE table_name = 'specification_requests' 
  AND column_name = 'value_chain_links';

-- Expected result: Both queries should return 1 row showing:
-- column_name: value_chain_links
-- data_type: jsonb
-- column_default: '[]'::jsonb

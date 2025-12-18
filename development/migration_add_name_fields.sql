-- Migration: Add first_name and last_name to specification_requests
-- Date: 2025-01-XX
-- Description: Adds contact person name fields to specification requests for better communication

ALTER TABLE specification_requests 
ADD COLUMN IF NOT EXISTS first_name VARCHAR(255),
ADD COLUMN IF NOT EXISTS last_name VARCHAR(255);

-- Verify the columns were added
SELECT column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_name = 'specification_requests'
AND column_name IN ('first_name', 'last_name');


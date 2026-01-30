-- Verification Query: Check if value_chain_links migration was successful
-- Run this AFTER running migration_add_value_chain_links.sql
-- Expected: Both queries should return 1 row each

-- ============================================
-- VERIFICATION 1: Check newsletter_specifications table
-- ============================================
SELECT 
    'newsletter_specifications' AS table_name,
    column_name, 
    data_type, 
    column_default,
    CASE 
        WHEN column_name = 'value_chain_links' THEN '✅ Column exists!'
        ELSE '❌ Column NOT found'
    END AS status
FROM information_schema.columns 
WHERE table_name = 'newsletter_specifications' 
  AND column_name = 'value_chain_links';

-- ============================================
-- VERIFICATION 2: Check specification_requests table
-- ============================================
SELECT 
    'specification_requests' AS table_name,
    column_name, 
    data_type, 
    column_default,
    CASE 
        WHEN column_name = 'value_chain_links' THEN '✅ Column exists!'
        ELSE '❌ Column NOT found'
    END AS status
FROM information_schema.columns 
WHERE table_name = 'specification_requests' 
  AND column_name = 'value_chain_links';

-- ============================================
-- VERIFICATION 3: Quick check - count columns
-- ============================================
-- This should return 2 rows (one for each table) if migration was successful
SELECT 
    table_name,
    COUNT(*) AS value_chain_links_column_count
FROM information_schema.columns 
WHERE table_name IN ('newsletter_specifications', 'specification_requests')
  AND column_name = 'value_chain_links'
GROUP BY table_name;

-- Expected result: 2 rows
-- newsletter_specifications | 1
-- specification_requests    | 1
